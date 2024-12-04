package kr.hyunwns.exam.kickboard_java.DTO;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter @Setter
public class ViolationDTO {
    private String violation_id;
    private String trackingId;
    private String violation_type;
    private LocalDateTime violation_date;
    private Float violation_duration;
    private String imageUrl;
}
