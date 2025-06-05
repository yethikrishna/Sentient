# src/server/main/voice/tts_services/orpheus_tts.py
import snac
import torch
import numpy as np
import asyncio
from llama_cpp import Llama, CreateCompletionStreamResponse
import os
from dotenv import load_dotenv # Orpheus has its own .env loading, might conflict or be redundant
import threading
import time
import traceback 
from typing import (
    AsyncGenerator,
    Generator,
    Literal,
    Optional,
    TypedDict,
    cast,
    Iterator,
    Tuple
)
from numpy.typing import NDArray

from .base_tts import BaseTTS, TTSOptionsBase # Import base class

# Orpheus specific .env loading - consider if this should be harmonized with main config
# For now, keeping its original behavior. If ORPHEUS_MODEL_PATH is set in main .env, that should be preferred.
# dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env") # Path from tts_services to server/.env
# load_dotenv(dotenv_path=dotenv_path, override=True) # Override to ensure these specific vars are used if set here.


# Define Orpheus-specific options, inheriting or adapting TTSOptionsBase if needed
class OrpheusTTSOptions(TTSOptionsBase, total=False): # total=False for TypedDict partial options
    max_tokens: int
    temperature: float
    top_p: float
    repetition_penalty: float
    voice_id: Literal["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"]


DEFAULT_MODEL_PATH_ORPHEUS = os.path.join(os.path.dirname(__file__), "..", "legacy", "voice", "models", "orpheus-3b-0.1-ft-q4_k_m.gguf") # Original default path
DEFAULT_N_GPU_LAYERS_ORPHEUS = int(os.getenv("ORPHEUS_N_GPU_LAYERS", 0))

SAMPLE_RATE = 24000
AVAILABLE_VOICES: list[Literal["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"]] = ["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"]
DEFAULT_VOICE: Literal["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"] = "tara"
CUSTOM_TOKEN_PREFIX = "<custom_token_"

class OrpheusTTS(BaseTTS):
    SAMPLE_RATE = SAMPLE_RATE
    AVAILABLE_VOICES = AVAILABLE_VOICES
    DEFAULT_VOICE = DEFAULT_VOICE
    CUSTOM_TOKEN_PREFIX = CUSTOM_TOKEN_PREFIX

    def __init__(
        self,
        model_path: str | None = None, # This will come from main config.py
        n_gpu_layers: int | None = None, # This will come from main config.py
        verbose: bool = False,
        n_ctx: int = 2048, 
        default_voice_id: Literal["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"] = DEFAULT_VOICE
    ):
        # Use main config for model_path and n_gpu_layers
        from ...config import ORPHEUS_MODEL_PATH as MAIN_ORPHEUS_MODEL_PATH
        from ...config import ORPHEUS_N_GPU_LAYERS as MAIN_ORPHEUS_N_GPU_LAYERS

        self.model_path = model_path or MAIN_ORPHEUS_MODEL_PATH
        self.n_gpu_layers = n_gpu_layers if n_gpu_layers is not None else MAIN_ORPHEUS_N_GPU_LAYERS
        self.verbose = verbose
        self.n_ctx = n_ctx

        if default_voice_id in self.AVAILABLE_VOICES:
            self.instance_default_voice = default_voice_id
        else:
            print(f"Warning: Provided default_voice_id '{default_voice_id}' is invalid. Falling back to class default '{self.DEFAULT_VOICE}'.")
            self.instance_default_voice = self.DEFAULT_VOICE
        print(f"OrpheusTTS instance configured with default voice: {self.instance_default_voice}, model: {self.model_path}")
        
        self.snac_model = None
        self.llm = None
        self.snac_device = "cpu"
        self._load_models()

    def _load_models(self):
        if self.snac_model is None:
            try:
                print("Loading SNAC model...")
                self.snac_model = snac.SNAC.from_pretrained("hubertsiuzdak/snac_24khz", weights_only=True).eval() # type: ignore
                self.snac_device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
                print(f"SNAC model using device: {self.snac_device}")
                self.snac_model = self.snac_model.to(self.snac_device)
                print("SNAC model loaded.")
            except TypeError: # Fallback if weights_only is not supported by the installed snac version
                 print("Loading SNAC model (without weights_only)...")
                 self.snac_model = snac.SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval() # type: ignore
                 self.snac_device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
                 print(f"SNAC model using device: {self.snac_device}")
                 self.snac_model = self.snac_model.to(self.snac_device)
                 print("SNAC model loaded.")
            except Exception as e:
                print(f"Error loading SNAC model: {e}")
                raise RuntimeError("Failed to load SNAC model") from e

        if self.llm is None:
            if not self.model_path or not os.path.exists(self.model_path):
                print(f"Error: Orpheus model not found at {self.model_path}")
                raise FileNotFoundError(f"Orpheus model not found at {self.model_path}")
            try:
                print(f"Loading Orpheus model from {self.model_path} with n_ctx={self.n_ctx}...")
                self.llm = Llama(
                    model_path=self.model_path,
                    n_gpu_layers=self.n_gpu_layers,
                    verbose=self.verbose,
                    n_ctx=self.n_ctx 
                )
                print(f"Orpheus model loaded with {self.n_gpu_layers} layers offloaded to GPU.")
            except Exception as e:
                print(f"Error loading Orpheus model: {e}")
                traceback.print_exc()
                raise RuntimeError(f"Failed to load Orpheus LLM: {e}") from e

    def _format_prompt(self, prompt: str, voice: Optional[Literal["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"]] = None) -> str:
        resolved_voice = voice or self.instance_default_voice
        if voice is not None and voice not in self.AVAILABLE_VOICES:
            print(f"Warning: Voice '{voice}' specified in options is invalid. Using instance default '{self.instance_default_voice}' instead.")
            resolved_voice = self.instance_default_voice
        formatted_prompt = f"{resolved_voice}: {prompt}"
        special_start = "<|audio|>"
        special_end = "<|eot_id|>"
        return f"{special_start}{formatted_prompt}{special_end}"

    def _turn_token_into_id(self, token_string: str, index: int) -> int | None:
        token_string = token_string.strip()
        last_token_start = token_string.rfind(self.CUSTOM_TOKEN_PREFIX)
        if last_token_start == -1: return None
        last_token = token_string[last_token_start:]
        if last_token.startswith(self.CUSTOM_TOKEN_PREFIX) and last_token.endswith(">"):
            try:
                number_str = last_token[len(self.CUSTOM_TOKEN_PREFIX):-1]
                token_id = int(number_str) - 10 - ((index % 7) * 4096)
                return token_id
            except ValueError: return None
        return None

    def _snac_decode_sync(self, multiframe: list[int]) -> NDArray[np.float32] | None:
        if self.snac_model is None: return None
        VALID_MIN_ID, VALID_MAX_ID = 0, 4095
        valid_ids = [id_val for id_val in multiframe if VALID_MIN_ID <= id_val <= VALID_MAX_ID]
        if len(valid_ids) < 28: return None
        
        frame = valid_ids[-28:]
        num_frames = len(frame) // 7
        codes_0 = torch.tensor([frame[7*j] for j in range(num_frames)], device=self.snac_device, dtype=torch.int32)
        codes_1 = torch.tensor([frame[7*j+1] for j in range(num_frames)] + [frame[7*j+4] for j in range(num_frames)], device=self.snac_device, dtype=torch.int32)
        codes_2 = torch.tensor([frame[7*j+k] for j in range(num_frames) for k in [2,3,5,6]], device=self.snac_device, dtype=torch.int32)

        if codes_0.numel() == 0 or codes_1.numel() == 0 or codes_2.numel() == 0: return None
        codes = [codes_0.unsqueeze(0), codes_1.unsqueeze(0), codes_2.unsqueeze(0)]
        
        try:
            with torch.inference_mode(): audio_hat = self.snac_model.decode(codes)
            audio_slice_tensor = audio_hat[:, :, 2048:4096].squeeze() # type: ignore
            audio_slice_np = audio_slice_tensor.cpu().numpy().astype(np.float32)
            return audio_slice_np.flatten() if audio_slice_np.ndim > 1 else audio_slice_np
        except RuntimeError as e:
            if "CUDA error: device-side assert triggered" in str(e):
                print(f"ERROR: CUDA assert in snac_model.decode. Inputs: c0={codes[0].shape}, c1={codes[1].shape}, c2={codes[2].shape}")
            else: print(f"RuntimeError during SNAC decoding: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during SNAC decoding: {e}"); traceback.print_exc()
            return None

    def _generate_tokens_sync(self, text: str, options: OrpheusTTSOptions | None = None) -> Generator[str, None, None]:
        if self.llm is None: yield "<|error|>"; return
        opts = options or {}
        voice = opts.get("voice_id", self.instance_default_voice)
        formatted_prompt = self._format_prompt(text, voice)
        try:
            response_stream = self.llm(
                prompt=formatted_prompt, max_tokens=opts.get("max_tokens", 4096),
                temperature=opts.get("temperature", 0.7), top_p=opts.get("top_p", 0.9),
                repeat_penalty=opts.get("repetition_penalty", 1.1), stream=True
            )
            for data in cast(Iterator[CreateCompletionStreamResponse], response_stream):
                if 'choices' in data and data['choices'] and 'text' in data['choices'][0]:
                    yield data['choices'][0]['text'] or "" 
        except Exception as e:
            print(f"Error during Orpheus token generation: {e}"); yield "<|error|>"

    def stream_tts_sync_internal(self, text: str, options: OrpheusTTSOptions | None = None) -> Generator[tuple[int, NDArray[np.float32]], None, None]:
        token_gen = self._generate_tokens_sync(text, options)
        buffer, count = [], 0
        for token_text in token_gen:
            if token_text == "<|error|>": break
            token_id = self._turn_token_into_id(token_text, count)
            if token_id is not None and token_id > 0: # Ensure token_id > 0, as 0 might be valid but problematic
                buffer.append(token_id); count += 1
                if count % 7 == 0 and len(buffer) >= 28:
                    audio_slice_np = self._snac_decode_sync(buffer)
                    if audio_slice_np is not None and audio_slice_np.size > 0:
                        yield (self.SAMPLE_RATE, audio_slice_np)

    async def stream_tts(self, text: str, options: TTSOptionsBase = None) -> AsyncGenerator[Tuple[int, NDArray[np.float32]], None]:
        # Cast options to OrpheusTTSOptions, or handle if it's just TTSOptionsBase
        orpheus_options: OrpheusTTSOptions = cast(OrpheusTTSOptions, options) if options else {}
        
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Optional[Tuple[int, NDArray[np.float32]]]] = asyncio.Queue()

        def thread_worker():
            try:
                for chunk in self.stream_tts_sync_internal(text, orpheus_options):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as e:
                print(f"Error in OrpheusTTS worker thread: {e}"); traceback.print_exc()
                loop.call_soon_threadsafe(queue.put_nowait, None) # Signal error with None
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None) # Signal end of stream
        
        thread = threading.Thread(target=thread_worker, daemon=True); thread.start()
        while True:
            chunk = await queue.get()
            if chunk is None: 
                queue.task_done(); break
            yield chunk
            queue.task_done()
        
        await asyncio.to_thread(thread.join) # Ensure thread finishes before exiting async generator

    def tts(self, text: str, options: OrpheusTTSOptions | None = None) -> tuple[int, NDArray[np.float32]]:
        all_chunks = [c_np for _, c_np in self.stream_tts_sync_internal(text, options) if c_np is not None and c_np.size > 0]
        return (self.SAMPLE_RATE, np.concatenate(all_chunks) if all_chunks else np.array([], dtype=np.float32))