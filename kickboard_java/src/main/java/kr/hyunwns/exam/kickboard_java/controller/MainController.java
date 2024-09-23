package kr.hyunwns.exam.kickboard_java.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class MainController {

    @GetMapping("/")
    public String home() {
        return "home";
    }

    @GetMapping("/crackdown")
    public String crackdown() {
        return "crackdown";
    }

    @GetMapping("/stats")
    public String stat() {
        return "stats";
    }


}
