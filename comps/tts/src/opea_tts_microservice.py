# Copyright (C) 2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import base64
import os
import time

import requests
from fastapi.responses import StreamingResponse
from integrations.gptsovits import OpeaGptsovitsTts
from integrations.speecht5 import OpeaSpeecht5Tts

from comps import (
    CustomLogger,
    OpeaComponentLoader,
    ServiceType,
    opea_microservices,
    register_microservice,
    register_statistics,
    statistics_dict,
)
from comps.cores.mega.constants import MCPFuncType
from comps.cores.proto.api_protocol import AudioSpeechRequest

logger = CustomLogger("opea_tts_microservice")
logflag = os.getenv("LOGFLAG", False)

tts_component_name = os.getenv("TTS_COMPONENT_NAME", "OPEA_SPEECHT5_TTS")
enable_mcp = os.getenv("ENABLE_MCP", "").strip().lower() in {"true", "1", "yes"}

# Initialize OpeaComponentLoader
loader = OpeaComponentLoader(tts_component_name, description=f"OPEA TTS Component: {tts_component_name}")


async def stream_forwarder(response):
    """Forward the stream chunks to the client using iter_content."""
    for chunk in response.iter_content(chunk_size=1024):
        yield chunk


@register_microservice(
    name="opea_service@tts",
    service_type=ServiceType.TTS,
    endpoint="/v1/audio/speech",
    host="0.0.0.0",
    port=9088,
    input_datatype=AudioSpeechRequest,
    output_datatype=StreamingResponse,
    enable_mcp=enable_mcp,
    mcp_func_type=MCPFuncType.TOOL,
    description="Convert text to audio.",
)
@register_statistics(names=["opea_service@tts"])
async def text_to_speech(request: AudioSpeechRequest) -> StreamingResponse:
    start = time.time()

    if logflag:
        logger.info(f"Input received: {request}")

    try:
        # Use the loader to invoke the component
        tts_response: requests.models.Response = await loader.invoke(request)
        if logflag:
            logger.info(tts_response)
        statistics_dict["opea_service@tts"].append_latency(time.time() - start, None)
        if enable_mcp:
            # return the base64 string
            audio_base64 = base64.b64encode(tts_response.content).decode("utf-8")

            return {"audio_str": audio_base64}
        else:
            return StreamingResponse(stream_forwarder(tts_response))

    except Exception as e:
        logger.error(f"Error during tts invocation: {e}")
        raise


if __name__ == "__main__":
    logger.info("OPEA TTS Microservice is starting....")
    opea_microservices["opea_service@tts"].start()
