const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const startButton = document.getElementById('start');
const stopButton = document.getElementById('stop');
const image = document.getElementById("annotatedImage");
const selectBox = document.getElementById('selectBox');

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
        sendFrameInterval = setInterval(sendFrame, 100);
    };

    socket.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
            waitingText.style.display = 'none';
            image.style.display = 'block';

            const blob = new Blob([event.data], {type: 'image/jpeg'});
            image.src = URL.createObjectURL(blob);


        } else {
            console.log('fail');
        }
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

        // 이미지 품질과 해상도를 조절하여 데이터 크기 최적화
        canvas.toBlob((blob) => {
            if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(blob);
            lastSendTime = currentTime();
            }
        }, 'image/jpeg', 0.3); // 이미지 포맷과 품질 설정 (품질 범위: 0.0 ~ 1.0)

    }
}


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
}

selectBox.onchange = async () => {
    try {
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
        }

        const selectedDeviceId = selectBox.value;
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 640 },
                deviceId : {exact: selectedDeviceId},
                frameRate: {ideal: 30}
            },
            audio: false
        });
        video.srcObject = mediaStream;

    } catch (error){
        console.error('오류:', err);
    }

}

// 스트림 시작
startButton.onclick = async () => {
    if(selectBox.value === "") {
        alert('장치 미디어를 선택해주세요');
        return;
    }
    try {
        const selectedDeviceId = selectBox.value;

        // 사용자 미디어 (카메라) 접근
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 640 },
                deviceId : {exact: selectedDeviceId},
                frameRate: {ideal: 30}
            },
            audio: false
        });

        video.srcObject = mediaStream

        // WebSocket 연결
        connectWebSocket();
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

    image.style.display = 'none';
    waitingText.style.display = 'block';

    console.log("스트림 중지");
};
