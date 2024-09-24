const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const startButton = document.getElementById('start');
const stopButton = document.getElementById('stop');

let mediaStream = null;
let sendFrameInterval = null;
let socket = null;

let lastSendTime = 0;

// WebSocket 연결 설정
function connectWebSocket() {

    socket = new WebSocket('wss://kickboard.duckdns.org:5000/video');
    socket.binaryType = 'arraybuffer';

    socket.onopen = () => {
        console.log('WebSocket 연결 성공');
    };

    socket.onmessage = (event) => {
        // 서버로부터 메시지 수신 시 처리 (필요 시 구현)
        console.log('서버 메시지:', event.data);
    };

    socket.onclose = () => {
        console.log('WebSocket 연결 종료');
    };

    socket.onerror = (error) => {
        console.error('WebSocket 에러:', error);
    };
}

function sendFrame() {
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
        const canvasContext = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvasContext.drawImage(video, 0, 0, canvas.width, canvas.height);

        let currentTime = Date.now;
        if (currentTime() > lastSendTime) {
            // 이미지 품질과 해상도를 조절하여 데이터 크기 최적화
            canvas.toBlob((blob) => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(blob);
                lastSendTime = currentTime();
            }
        }, 'image/jpeg', 0.5); // 이미지 포맷과 품질 설정 (품질 범위: 0.0 ~ 1.0)
        }

    }
}

// 스트림 시작
startButton.onclick = async () => {
    try {
        // 사용자 미디어 (카메라) 접근
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 384 },
                height: { ideal: 640 },
                facingMode : {exact: "environment"},
                frameRate: {ideal: 15, max:30}
            },
            audio: false
        });
        video.srcObject = mediaStream

        // WebSocket 연결
        connectWebSocket();
        // 일정 간격으로 프레임 캡쳐 및 전송
        setInterval(sendFrame, 100);
        console.log('스트림 시작');
    } catch (err) {
        console.error('오류:', err);
    }
};

// 스트림 중지
stopButton.onclick = () => {
    if (sendFrameInterval) {
        clearInterval(sendFrameInterval);
        sendFrameInterval = null;
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
    if (socket) {
        socket.close();
    }
    console.log("스트림 중지");
};
