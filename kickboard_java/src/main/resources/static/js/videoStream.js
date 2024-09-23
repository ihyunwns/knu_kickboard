const socketServerUrl = 'wss://124.60.219.97:8443/video';

const socket = new WebSocket(socketServerUrl);
socket.binaryType = 'arraybuffer';

const notConnectedMessage = document.getElementById('not_connected_message');
var mediaSource = new MediaSource();

// Create a video element to display the streamed video
const video = document.getElementById('video');
console.log(video);
// Assign the MediaSource object to the video element
video.src = URL.createObjectURL(mediaSource);

mediaSource.addEventListener('sourceopen', () => {
    console.log('MediaSource is open');

    const mimeType = 'video/webm; codecs="vp8"';
    if (!MediaSource.isTypeSupported(mimeType)) {
        console.error(`MIME type ${mimeType} is not supported`);
        return;
    }
    // Create a new SourceBuffer
    var sourceBuffer = mediaSource.addSourceBuffer(mimeType);
    console.log('SourceBuffer created with MIME type:', mimeType);

    // When a chunk of data is received from the WebSocket
    socket.onmessage = (event) => {
        console.log('WebSocket message received, size:', event.data.byteLength);
        const arrayU8 = new Uint8Array(event.data);
        // Check if the MediaSource is still open
        if (mediaSource.readyState === 'open') {
            // Append the received data to the SourceBuffer
            sourceBuffer.appendBuffer(arrayU8);
            console.log('Appended buffer:', arrayU8.byteLength);
        } else {
            console.log('Media source is not in open state: ', mediaSource.readyState);
        }
    };

    // When the SourceBuffer has enough data to start playing
    sourceBuffer.addEventListener('updateend', () => {
        // If the video element is not already playing, start playing it
        if (video.paused) {
            video.play().then(() => {
                console.log('Video started playing');
                notConnectedMessage.style.display = 'none';
            }).catch(err => {
                console.error('Error playing video:', err);
            });

        }
    });

    sourceBuffer.addEventListener('error', (event) => {
        console.error('SourceBuffer error:', event);
    });
});


// When a WebSocket error occurs
socket.onerror = (error) => {
    console.error('WebSocket error:', error);
};

// When the WebSocket connection is closed
socket.onclose = () => {
    console.log('WebSocket connection closed.');
};

