package kr.hyunwns.exam.kickboard_java.controller;

import kr.hyunwns.exam.kickboard_java.DTO.ViolationCountDTO;
import kr.hyunwns.exam.kickboard_java.DTO.ViolationDTO;
import kr.hyunwns.exam.kickboard_java.service.ViolationService;
import kr.hyunwns.exam.kickboard_java.util.FineCalculate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

import java.io.File;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Controller
public class MainController {

    private final ViolationService violationService;

    @Autowired
    public MainController(ViolationService violationService) {
        this.violationService = violationService;
    }

    @GetMapping("/")
    public String home() {
        return "home";
    }

    @GetMapping("/crackdown")
    public String crackdown() {
        return "crackdown";
    }

    @GetMapping("/stats")
    public String stat(Model model) {
        ViolationDTO violation = new ViolationDTO();
        List<ViolationDTO> todayViolations = violationService.getTodayViolations();

        List<ViolationCountDTO> weeklyCounts = violationService.getWeekViolationsCounts();
        List<ViolationCountDTO> monthlyCounts = violationService.getMonthViolationsCounts();

        int todayFine = FineCalculate.fineCalculate(todayViolations);

        List<ViolationDTO> totalViolations = violationService.getAllViolations();
        int totalFine = FineCalculate.fineCalculate(totalViolations);

        List<ViolationDTO> weekViolations = violationService.getWeekViolations();
        int weeklyFine = FineCalculate.fineCalculate(weekViolations);

        List<ViolationDTO> monthViolations = violationService.getMonthViolations();
        int monthlyFine = FineCalculate.fineCalculate(monthViolations);

        model.addAttribute("todayFine", todayFine);
        model.addAttribute("totalFine", totalFine);
        model.addAttribute("weeklyFine", weeklyFine);
        model.addAttribute("monthlyFine", monthlyFine);

        model.addAttribute("todayViolations", todayViolations);

        // 카운트용
        model.addAttribute("weeklyCounts", weeklyCounts);
        model.addAttribute("monthlyCounts", monthlyCounts);

        return "stats";
    }

    @GetMapping(value = "/display/{violation_id}")
    public String display(@PathVariable("violation_id") String id, Model model) {

        ViolationDTO violation = violationService.getViolationById(id);
        LocalDateTime violationDate = violation.getViolation_date();

        String year = Integer.toString(violationDate.getYear());
        String month = Integer.toString(violationDate.getMonthValue());
        String day = Integer.toString(violationDate.getDayOfMonth());

        String subPath = year + "-" + month + "/" + "day " + day + "/" + violation.getTrackingId() ;

        String imageFolderPath = violation.getImageUrl();

        File folder = new File(imageFolderPath);
        List<String> imageUrls = new ArrayList<>();

        if (folder.exists() && folder.isDirectory()) {
            File[] files = folder.listFiles((dir, name) -> {
                String lowercaseName = name.toLowerCase();
                return lowercaseName.endsWith(".jpg");
            });

            if (files != null) {
                for (File file : files) {
                    // 이미지 파일의 웹 접근 가능한 URL 생성
                    String imageUrl = "/images/" + subPath + "/" + file.getName();
                    imageUrls.add(imageUrl);
                }
            }
        }

        model.addAttribute("violation", violation);
        model.addAttribute("imageUrls", imageUrls);

        return "viewImage";
    }



}
