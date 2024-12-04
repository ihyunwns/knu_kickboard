package kr.hyunwns.exam.kickboard_java.controller;

import kr.hyunwns.exam.kickboard_java.DTO.ViolationDTO;
import kr.hyunwns.exam.kickboard_java.service.ViolationService;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

import java.util.List;

@Controller
public class ManagerController {

    private final ViolationService violationService;
    public ManagerController(ViolationService violationService) {
        this.violationService = violationService;
    }

    @GetMapping("/manage")
    public String manage(Model model) {
        List<ViolationDTO> allViolations = violationService.getAllViolations();

        model.addAttribute("totalViolations", allViolations);

        return "manage";
    }

    @GetMapping(value = "/delete/{violation_id}")
    public String delete(@PathVariable String violation_id) {
        violationService.deleteViolation(violation_id);

        return "redirect:/manage";
    }
}
