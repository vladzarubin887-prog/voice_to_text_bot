import time
from faster_whisper import WhisperModel

class WhisperService:
    def __init__(self, model_size: str = "small", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self.model = None
    
    def _ensure_model_loaded(self):
        if self.model is None:
            print(f"🔊 Загрузка модели Whisper {self.model_size}...")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type="int8",
                download_root="models/"
            )
            print("✅ Модель загружена")
    
    def transcribe(self, audio_path: str):
        self._ensure_model_loaded()
        
        start_time = time.time()
        
        segments, info = self.model.transcribe(
            audio_path,
            language=None,
            task="transcribe",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=True,
            initial_prompt="Это транскрипция речи. Расставь знаки препинания."
        )
        
        detected_language = info.language
        
        full_text = []
        for segment in segments:
            full_text.append(segment.text)
        
        text = " ".join(full_text)
        text = " ".join(text.split())
        
        elapsed = time.time() - start_time
        
        return text, detected_language, elapsed