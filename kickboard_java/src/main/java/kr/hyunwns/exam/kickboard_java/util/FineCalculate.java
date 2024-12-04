package kr.hyunwns.exam.kickboard_java.util;

import kr.hyunwns.exam.kickboard_java.DTO.ViolationDTO;

import java.util.List;

public class FineCalculate {

    public static int fineCalculate(List<ViolationDTO> lists) {
        int fine = 0;

        for (ViolationDTO v : lists) {
             String violationType = v.getViolation_type();
            if (violationType.equals("HELMET")){
                fine += 20000;
            } else if (violationType.equals("2-PERSON")){
                fine += 40000;
            } else{
                fine += 60000;
            }
        }
        return fine;
    }
}
