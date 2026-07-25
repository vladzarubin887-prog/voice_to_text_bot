import os
from pathlib import Path
from pydub import AudioSegment

class AudioProcessor:
    def __init__(self, temp_folder: str = "temp"):
        self.temp_folder = Path(temp_folder)
        self.temp_folder.mkdir(exist_ok=True)
    
    async def download_audio(self, file, file_id: str):
        file_path = self.temp_folder / f"{file_id}.ogg"
        await file.download_to_drive(file_path)
        return str(file_path)
    
    async def convert_to_wav(self, ogg_path: str):
        wav_path = ogg_path.replace('.ogg', '.wav')
        
        audio = AudioSegment.from_file(ogg_path, format="ogg")
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(wav_path, format="wav")
        
        return wav_path
    
    async def get_duration(self, file_path: str):
        try:
            audio = AudioSegment.from_file(file_path)
            return int(len(audio) / 1000)
        except:
            return 0
    
    async def cleanup(self, *paths):
        for path in paths:
            if path and Path(path).exists():
                try:
                    Path(path).unlink()
                except:
                    pass