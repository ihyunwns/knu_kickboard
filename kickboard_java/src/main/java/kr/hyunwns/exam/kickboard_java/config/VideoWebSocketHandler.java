package kr.hyunwns.exam.kickboard_java.config;

import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.BinaryMessage;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.BinaryWebSocketHandler;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Component
@Slf4j
public class VideoWebSocketHandler extends BinaryWebSocketHandler {

    private final String storageDirectory;
    private static final Logger logger = LoggerFactory.getLogger(VideoWebSocketHandler.class);

    private static Map<String, FileOutputStream> sessionFileMap = new ConcurrentHashMap<>();
    private final ExecutorService executor = Executors.newFixedThreadPool(10); // 스레드 풀 생성

    private static Map<String, Socket> socketList = new ConcurrentHashMap<>();

    public VideoWebSocketHandler(@Value("${video.storage.directory}") String storageDirectory) {
        this.storageDirectory = storageDirectory;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        logger.info("Session ID: {} 가 연결되었습니다.", session.getId());

        File dir = new File(storageDirectory);

        if(!dir.exists()){
            boolean dirCreated = dir.mkdirs();
            if (dirCreated) {
                logger.info("저장 디렉토리 생성: {}", dir.getAbsolutePath());
            } else {
                logger.info("저장 디렉토리 생성 실패 {}", dir.getAbsolutePath());
                throw new IOException("저장 디렉토리 생성 실패");
            }
        }

        String now = LocalDateTime.now().toString().split("\\.")[0];
        String createdAt = now.replace(":", "_");
        String filePath = storageDirectory + File.separator + "received_video_" + createdAt + session.getId() + ".webm";

        Socket pythonSocket = new Socket("localhost", 5000);
        socketList.put(session.getId(), pythonSocket);

        FileOutputStream fos = new FileOutputStream(filePath, true);
        sessionFileMap.put(session.getId(), fos);

    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        logger.info("Session ID: {} 의 연결이 종료되었습니다. \n{}", session.getId(), status.getReason() == null ? "" : status.getReason());
        FileOutputStream fos = sessionFileMap.remove(session.getId());
        Socket pySocket = socketList.remove(session.getId());

        if(pySocket != null){
            pySocket.close();
        }
        if(fos != null) {
            try {
                fos.flush();  // 남은 데이터를 파일에 모두 기록
            } catch (IOException e) {
                logger.error("Error flushing video data to file: {}", e.getMessage());
            } finally {
                try {
                    fos.close();  // 파일 스트림 종료
                    logger.info("File stream closed for session: {}", session.getId());
                } catch (IOException e) {
                    logger.error("Error closing file stream: {}", e.getMessage());
                }
            }
        }
    }

    @Override
    protected void handleBinaryMessage(WebSocketSession session, BinaryMessage message) throws Exception {
        ByteBuffer payload = message.getPayload();
        FileOutputStream outputStream = sessionFileMap.get(session.getId());

        if(outputStream != null) {
            executor.submit(() -> {
                try {
                    byte[] videoData = payload.array();
                    outputStream.write(videoData);

                    OutputStream ops = socketList.get(session.getId()).getOutputStream();
                    ops.write(videoData);
                    ops.flush();

                    logger.info("Received video data of size: {}", message.getPayloadLength());
                } catch (IOException e) {
                    logger.error(e.getMessage());
                }
            });
        }
    }

    @PreDestroy
    public void shutdown() {
        executor.shutdown();
        logger.info("ExecutorService 종료됨");
    }
}
