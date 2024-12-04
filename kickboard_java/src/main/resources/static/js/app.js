const remoteVideo = document.getElementById('remoteVideo');
const startButton = document.getElementById('start');
const stopButton = document.getElementById('stop');
const selectBox = document.getElementById('selectBox');
const waitingText = document.getElementById('waitingMessage');

let mediaStream = null;
let peerConnection = null;
let signalingSocket = null;

const configuration = {
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
};

window.onload = () => {
    navigator.mediaDevices.getUserMedia({ video: true })
    .then(() => {
        // 권한이 허용되면 장치 목록 나열
        navigator.mediaDevices.enumerateDevices()
            .then(devices => {
                devices.forEach(device => {
                    if (device.kind === 'videoinput') {

                        var option = document.createElement('option');
                        option.text = device.label;
                        option.value = device.deviceId;

                        selectBox.options.add(option);
                    }
                });
            })
            .catch(err => {
                console.error('장치 나열 실패:', err);
            });
    })
    .catch(err => {
        console.error('카메라 접근 실패:', err);
    });
};

startButton.onclick = async () => {
    console.log('START')
    try {
        const selectedDeviceId = selectBox.value;

        if (!selectedDeviceId) {
            alert('카메라 장치를 선택해주세요.');
            return;
        }

        selectBox.disabled = true;

        mediaStream = await navigator.mediaDevices.getUserMedia( {
            video: {
                width: { min: 640, ideal: 640, max: 640 },
                height: { min: 640, ideal: 640, max: 640 },
                deviceId: { exact: selectedDeviceId },
                frameRate: { ideal: 30, max: 30 }
            }, audio: false });

        peerConnection = new RTCPeerConnection(configuration);

        // 미디어 스트림의 모든 트랙을 RTCPeerConnection에 추가
        mediaStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, mediaStream);
        });

        peerConnection.ontrack = event => {
            console.log('서버로 부터 트랙 수신: ', event.track.kind);
            if (event.track.kind === 'video') {
                const [remoteStream] = event.streams;
                remoteVideo.srcObject = remoteStream;

                remoteVideo.onplaying = () => {
                    waitingText.style.display = 'none';
                    remoteVideo.style.display = 'block';
                }

                remoteVideo.onpause = () => {
                    waitingText.style.display = 'block';
                    remoteVideo.style.display = 'none';
                }

                remoteVideo.onended = () => {
                    waitingText.style.display = 'block';
                    remoteVideo.style.display = 'none';
                }

            }
        }

        //ICE 후보가 발견될 때마다 시그널링 서버로 전송
        peerConnection.onicecandidate = event => {
            if (event.candidate){
                signalingSocket.send(JSON.stringify({'candidate': event.candidate }))
            }
        }

        signalingSocket = new WebSocket('wss://kickboard.duckdns.org:5000');

        signalingSocket.onopen = async () => {
            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);
            signalingSocket.send(JSON.stringify({'sdp': peerConnection.localDescription }))
        }

        signalingSocket.onmessage = async (event) => {
            const message = JSON.parse(event.data);

            if (message.sdp) {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(message.sdp));
            } else if (message.candidate) {
                await peerConnection.addIceCandidate(new RTCIceCandidate(message.candidate));
            }
        }

    } catch (error) {
        console.error('오류:', error);
    }
};

stopButton.onclick = () => {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    if (signalingSocket) {
        signalingSocket.close();
        signalingSocket = null;
    }

    remoteVideo.srcObject = null;
    waitingText.style.display = 'block';
    remoteVideo.style.display = 'none';

    selectBox.disabled = false;

    console.log('스트림 중지');
};
