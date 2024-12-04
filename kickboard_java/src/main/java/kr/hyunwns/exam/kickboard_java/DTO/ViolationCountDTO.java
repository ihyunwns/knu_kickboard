package kr.hyunwns.exam.kickboard_java.DTO;

import lombok.Getter;
import lombok.Setter;

@Getter @Setter
public class ViolationCountDTO {
    private String period; // 날짜 또는 월
    private int count;      // 단속 횟수

    @Override
    public String toString() {
        return "ViolationCountDTO{" +
                "period='" + period + '\'' +
                ", count=" + count +
                '}';
    }
}

