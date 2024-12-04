import asyncio
import websockets
import ssl
import av
import json
import time
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaBlackhole
import cv2
import numpy as np
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack
from aiortc.sdp import candidate_from_sdp
from av import VideoFrame
from sympy import elliptic_pi

from process import process_frame

pcs = set()
av.logging.set_level(av.logging.ERROR)

class VideoTransformTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, track):
        super().__init__()  # don't forget this!
        self.track = track  # 클라이언트로부터 수신한 비디오 트랙\
        self.start_time = time.time()

    async def recv(self):
        frame = await self.track.recv()

        img = frame.to_ndarray(format="bgr24")
        img_resized = cv2.resize(img, (640, 640))

        loop = asyncio.get_event_loop()
        elapsed_time = time.time() - self.start_time

        processed_img = await loop.run_in_executor(None, process_frame, img_resized, elapsed_time)

        # 처리된 프레임을 PC에서 표시
        cv2.imshow("Processed Video", processed_img)
        cv2.waitKey(1)  # OpenCV 창을 업데이트하기 위해 필요

        # OpenCV 이미지를 VideoFrame으로 변환하여 클라이언트로 전송
        new_frame = VideoFrame.from_ndarray(processed_img, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base

        return new_frame

async def offer(websocket, path):
    print('클라이언트 연결됨')
    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("track")
    def on_track(track):
        print("트랙 수신:", track.kind)
        if track.kind == "video":
            # 수신한 트랙을 처리하여 클라이언트로 다시 전송할 트랙 생성
            local_video = VideoTransformTrack(track)
            pc.addTrack(local_video)

    try:
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            if "sdp" in data:
                # 클라이언트로부터 SDP offer 수신
                offer = RTCSessionDescription(
                    sdp=data["sdp"]["sdp"],
                    type=data["sdp"]["type"]
                )
                await pc.setRemoteDescription(offer)

                # SDP answer 생성 및 전송
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await websocket.send(json.dumps({
                    'sdp': {
                        'type': pc.localDescription.type,
                        'sdp': pc.localDescription.sdp
                    }
                }))

            elif "candidate" in data:
                # ICE 후보 수신
                candidate_dict = data["candidate"]
                if candidate_dict.get("candidate"):
                    candidate = candidate_from_sdp(candidate_dict["candidate"])
                    candidate.sdpMid = candidate_dict.get("sdpMid")
                    sdpMLineIndex = candidate_dict.get("sdpMLineIndex")
                    if sdpMLineIndex is not None:
                        candidate.sdpMLineIndex = int(sdpMLineIndex)
                    await pc.addIceCandidate(candidate)

    except websockets.exceptions.ConnectionClosed:
        print('클라이언트 연결 종료')
    finally:
        await pc.close()
        pcs.discard(pc)
        # OpenCV 창 닫기
        cv2.destroyAllWindows()


ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile=r'C:\Users\ihyun\kickboard_ssl\full_chain.crt', keyfile=r'C:\Users\ihyun\kickboard_ssl\private.key')

start_server = websockets.serve(offer, '0.0.0.0', 5000, ssl=ssl_context, max_size=None)
print("5000 PORT Running...")

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
