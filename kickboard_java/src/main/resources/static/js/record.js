socket.onopen = () => {
    console.log("Socket 연결 성공");
    navigator.mediaDevices.getUserMedia({
        audio: true,
        video: {
            width: 1280,
            height: 720,
            facingMode: {exact: "environment"}
        }
    })
        .then(stream => {
            console.log("Media stream obtained");

            const localVideo = document.getElementById('video');
            localVideo.srcObject = stream;

            let options = { mimeType: 'video/webm; codecs="vp8"' };
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options.mimeType = 'video/webm';
                if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                    options.mimeType = '';
                }
            }

            const mediaRecorder = new MediaRecorder(stream, options);
            mediaRecorder.start(1000);

            mediaRecorder.ondataavailable = (event) => {
                console.log('ondataavailable', event.data.size);
                if (event.data && event.data.size > 0) {
                    if (socket.readyState === WebSocket.OPEN) {
                        socket.send(event.data);
                    } else {
                        console.log("WebSocket is not open.")
                        mediaRecorder.stop();
                    }
                }
            }



        })
        .catch(error => {
            console.error('Error accessing media devices:', error);
        })
    ;
};

socket.onerror = (error) => {
    console.error('WebSocket error:', error);
};

// When the WebSocket connection is closed
socket.onclose = () => {
    console.log('WebSocket connection closed.');

};