from pydantic import BaseModel

class VoiceOfferRequest(BaseModel):
    sdp: str
    type: str

class VoiceAnswerResponse(BaseModel):
    sdp: str
    type: str
class VoiceUsageRequest(BaseModel):
    duration_seconds: int
