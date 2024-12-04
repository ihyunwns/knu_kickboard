package kr.hyunwns.exam.kickboard_java.repository;

import kr.hyunwns.exam.kickboard_java.DTO.ViolationCountDTO;
import kr.hyunwns.exam.kickboard_java.DTO.ViolationDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Repository
@Transactional(readOnly = true)
public class ViolationRepository {

    private final JdbcTemplate jdbcTemplate;
    private static final Logger logger = LoggerFactory.getLogger(ViolationRepository.class);

    @Autowired
    public ViolationRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    // RowMapper 구현
    private final RowMapper<ViolationDTO> violationRowMapper = (rs, rowNum) -> {
        ViolationDTO violation = new ViolationDTO();
        violation.setViolation_id(rs.getString("violation_id"));
        violation.setTrackingId(rs.getString("tracking_id"));
        violation.setViolation_type(rs.getString("violation_type"));
        violation.setViolation_date(rs.getTimestamp("violation_date").toLocalDateTime());
        violation.setViolation_duration(rs.getFloat("violation_duration"));
        violation.setImageUrl(rs.getString("image_url"));
        return violation;
    };

    // 오늘의 위반자 목록 조회
    public List<ViolationDTO> getTodayViolations() {
        String sql = "SELECT v.violation_id, v.tracking_id, vt.violation_type_name AS violation_type, v.violation_date, v.violation_duration, v.image_url " +
                     "FROM violation v " +
                     "JOIN violation_types vt ON v.violation_type_id = vt.violation_type_id " +
                     "WHERE DATE(v.violation_date) = ? " +
                     "ORDER BY v.violation_date DESC";
        LocalDateTime today = LocalDateTime.now();
        return jdbcTemplate.query(sql, violationRowMapper, today.toLocalDate());
    }

    // Violation ID로 위반자 단일 조회
    public ViolationDTO getViolationById(String id) {
        String sql = "SELECT v.violation_id, v.tracking_id, vt.violation_type_name AS violation_type, v.violation_date, v.violation_duration, v.image_url " +
                     "FROM violation v " +
                     "JOIN violation_types vt ON v.violation_type_id = vt.violation_type_id " +
                     "WHERE v.violation_id = ?";

        return jdbcTemplate.queryForObject(sql, violationRowMapper, id);

    }

    // 주간 단속 횟수 조회
    public List<ViolationCountDTO> getWeekViolationsCounts() {

        String sql = "SELECT DATE(violation_date) AS violation_day, COUNT(*) as count " +
                     "FROM violation " +
                     "WHERE violation_date >= CURDATE() - INTERVAL 6 DAY " +
                     "GROUP BY violation_day ";
                    // MySQL에서는 SELECT 문에서 쓰인 별칭을 쓸 수 있음 !

        RowMapper<ViolationCountDTO> rowMapper = (rs, rowNum) -> {
            ViolationCountDTO violationCountDTO = new ViolationCountDTO();
            violationCountDTO.setPeriod(rs.getString("violation_day"));
            violationCountDTO.setCount(rs.getInt("count"));

            return violationCountDTO;
        };

        return jdbcTemplate.query(sql, rowMapper);
    }

    // 월간 단속 횟수 조회
    public List<ViolationCountDTO> getMonthViolationsCounts() {
    String sql = "SELECT DATE_FORMAT(violation_date, '%Y-%m') AS violation_month, COUNT(*) AS count " +
                 "FROM violation " +
                 "WHERE violation_date >= DATE_SUB(CURDATE(), INTERVAL 11 MONTH) " +
                 "GROUP BY DATE_FORMAT(violation_date, '%Y-%m') ";

    RowMapper<ViolationCountDTO> rowMapper = (rs, rowNum) -> {
                ViolationCountDTO violationCountDTO = new ViolationCountDTO();
                violationCountDTO.setPeriod(rs.getString("violation_month"));
                violationCountDTO.setCount(rs.getInt("count"));

                return violationCountDTO;
        };

    return jdbcTemplate.query(sql, rowMapper);
}

    // 전체 조회
    public List<ViolationDTO> getAllViolations() {
        String sql = "SELECT v.violation_id, v.tracking_id, vt.violation_type_name AS violation_type, v.violation_date, v.violation_duration, v.image_url " +
                     "FROM violation v " +
                     "JOIN violation_types vt ON v.violation_type_id = vt.violation_type_id ";

        return jdbcTemplate.query(sql, violationRowMapper);
    }

    public List<ViolationDTO> getWeekViolations() {
        String sql = "SELECT v.violation_id, v.tracking_id, vt.violation_type_name AS violation_type, v.violation_date, v.violation_duration, v.image_url " +
                     "FROM violation v " +
                     "JOIN violation_types vt ON v.violation_type_id = vt.violation_type_id " +
                     "WHERE violation_date >= CURDATE() - INTERVAL 6 DAY ";

        return jdbcTemplate.query(sql, violationRowMapper);

    }

    public List<ViolationDTO> getMonthViolations() {
        String sql = "SELECT v.violation_id, v.tracking_id, vt.violation_type_name AS violation_type, v.violation_date, v.violation_duration, v.image_url " +
                     "FROM violation v " +
                     "JOIN violation_types vt ON v.violation_type_id = vt.violation_type_id " +
                     "WHERE violation_date >= DATE_SUB(CURDATE(), INTERVAL 11 MONTH) ";

        return jdbcTemplate.query(sql, violationRowMapper);

    }

    @Transactional
    public void remove(String id) {
        String sql = "DELETE FROM violation WHERE violation_id = ?";


        int rowsAffected = jdbcTemplate.update(sql, id);
        if (rowsAffected == 0) {
            logger.warn("Attempted to delete violation with id {} but no record found.", id);
            throw new RuntimeException();
        }
        logger.info("Violation with id {} successfully deleted.", id);

    }
}
