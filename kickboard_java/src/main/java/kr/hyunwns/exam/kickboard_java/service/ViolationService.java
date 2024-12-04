package kr.hyunwns.exam.kickboard_java.service;

import kr.hyunwns.exam.kickboard_java.DTO.ViolationCountDTO;
import kr.hyunwns.exam.kickboard_java.DTO.ViolationDTO;
import kr.hyunwns.exam.kickboard_java.repository.ViolationRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ViolationService {

    private final ViolationRepository violationRepository;

    @Autowired
    public ViolationService(ViolationRepository violationRepository) {
        this.violationRepository = violationRepository;
    }

    public List<ViolationDTO> getTodayViolations() {
        return violationRepository.getTodayViolations();
    }

    public ViolationDTO getViolationById(String id) {
        return violationRepository.getViolationById(id);
    }

    public List<ViolationDTO> getAllViolations() {
        return violationRepository.getAllViolations();
    }

    public List<ViolationCountDTO> getWeekViolationsCounts() {
        return violationRepository.getWeekViolationsCounts();
    }

    public List<ViolationCountDTO> getMonthViolationsCounts() {
        return violationRepository.getMonthViolationsCounts();
    }

    public List<ViolationDTO> getWeekViolations() {
        return violationRepository.getWeekViolations();
    }

    public List<ViolationDTO> getMonthViolations() {
        return violationRepository.getMonthViolations();
    }

    public void deleteViolation(String id) {
        violationRepository.remove(id);
    }

}
