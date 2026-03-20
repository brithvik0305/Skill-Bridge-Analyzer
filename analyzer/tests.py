from io import BytesIO
from django.test import TestCase
from unittest.mock import patch

from analyzer.utils import (
    process_resume_and_jd,
    analyze_gap_hybrid,
    fallback_roadmap,
    validate_ai_gap,
    calculate_match_score,
)


class ProcessResumeTests(TestCase):

    @patch("analyzer.utils.extract_job_skills_regex")
    @patch("analyzer.utils.generate_roadmap_hybrid")
    @patch("analyzer.utils.analyze_gap_hybrid")
    @patch("analyzer.utils.extract_text")
    def test_happy_path(
        self, mock_extract_text, mock_analyze_gap,
        mock_generate_roadmap, mock_extract_job_skills
    ):
        """Happy path: valid resume + JD returns full result"""
        mock_extract_text.return_value = "Python SQL"
        mock_extract_job_skills.return_value = ["Python", "Django", "SQL"]

        mock_analyze_gap.return_value = (
            [{"skill": "Django", "priority": "High", "reason": "Required skill"}],
            "fallback"
        )

        mock_generate_roadmap.return_value = (
            {
                "30_days": ["Learn Django basics"],
                "60_days": ["Build a Django app"],
                "90_days": ["Deploy project"]
            },
            "fallback"
        )

        fake_resume = BytesIO(b"fake pdf content")
        jd_text = "We need Python Django SQL experience"

        result = process_resume_and_jd(fake_resume, jd_text)

        self.assertIn("Python", result["matched"])
        self.assertIn("SQL", result["matched"])
        self.assertIn("Django", result["missing"])
        self.assertGreater(result["match_score"], 0)
        self.assertEqual(result["source"], "fallback")
        self.assertIn("roadmap", result)
        self.assertIn("30_days", result["roadmap"])

    @patch("analyzer.utils.extract_job_skills_regex")
    @patch("analyzer.utils.generate_roadmap_hybrid")
    @patch("analyzer.utils.analyze_gap_hybrid")
    @patch("analyzer.utils.extract_text")
    def test_edge_case_empty_resume(
        self, mock_extract_text, mock_analyze_gap,
        mock_generate_roadmap, mock_extract_job_skills
    ):
        """Edge case: empty resume text raises ValueError"""
        mock_extract_text.return_value = ""
        mock_extract_job_skills.return_value = ["Python"]

        fake_resume = BytesIO(b"fake pdf content")
        jd_text = "We need Python experience for this role"

        with self.assertRaises(ValueError) as ctx:
            process_resume_and_jd(fake_resume, jd_text)

        self.assertIn("extract text", str(ctx.exception).lower())

    @patch("analyzer.utils.extract_job_skills_regex")
    @patch("analyzer.utils.generate_roadmap_hybrid")
    @patch("analyzer.utils.analyze_gap_hybrid")
    @patch("analyzer.utils.extract_text")
    def test_edge_case_no_matched_skills(
        self, mock_extract_text, mock_analyze_gap,
        mock_generate_roadmap, mock_extract_job_skills
    ):
        """Edge case: user has no matching skills → match score is 0"""
        mock_extract_text.return_value = "cooking gardening painting"
        mock_extract_job_skills.return_value = ["Python", "Django", "SQL"]

        mock_analyze_gap.return_value = (
            [
                {"skill": "Python", "priority": "High", "reason": "Missing"},
                {"skill": "Django", "priority": "High", "reason": "Missing"},
                {"skill": "SQL", "priority": "Medium", "reason": "Missing"},
            ],
            "fallback"
        )

        mock_generate_roadmap.return_value = (
            {
                "30_days": ["Learn Python basics"],
                "60_days": ["Practice small projects"],
                "90_days": ["Solve advanced problems"]
            },
            "fallback"
        )

        fake_resume = BytesIO(b"fake pdf content")
        jd_text = "We need Python Django SQL experience for this role"

        result = process_resume_and_jd(fake_resume, jd_text)

        self.assertEqual(result["match_score"], 0)
        self.assertIn("Python", result["missing"])
        self.assertEqual(result["roadmap_source"], "fallback")

    @patch("analyzer.utils.extract_gap_ai")
    def test_analyze_gap_hybrid_falls_back_on_ai_failure(self, mock_extract_gap_ai):
        """Gap analysis uses fallback when AI raises an exception"""
        mock_extract_gap_ai.side_effect = Exception("AI unavailable")

        user_skills = ["Python"]
        job_skills = ["Python", "Django"]
        jd_text = "Python Django Django required for this role"

        result, source = analyze_gap_hybrid(user_skills, job_skills, jd_text)

        self.assertEqual(source, "fallback")
        self.assertIsInstance(result, list)
        self.assertTrue(any(item["skill"] == "Django" for item in result))

    def test_validate_ai_gap_rejects_empty_list(self):
        """Validation should reject an empty list"""
        self.assertFalse(validate_ai_gap([]))

    def test_validate_ai_gap_rejects_missing_keys(self):
        """Validation should reject items missing required keys"""
        self.assertFalse(validate_ai_gap([{"skill": "Python"}]))  # no priority

    def test_validate_ai_gap_accepts_valid_data(self):
        """Validation should accept a properly structured list"""
        self.assertTrue(validate_ai_gap([
            {"skill": "Python", "priority": "High", "reason": "Required"}
        ]))

    def test_calculate_match_score_zero_when_no_job_skills(self):
        """Match score should be 0 when job_skills is empty"""
        self.assertEqual(calculate_match_score(["Python"], []), 0)

    def test_calculate_match_score_full_match(self):
        """Match score should be 100 when all job skills are matched"""
        self.assertEqual(calculate_match_score(["Python", "SQL"], ["Python", "SQL"]), 100)

    def test_fallback_roadmap_covers_all_skills(self):
        """Fallback roadmap should distribute all gap skills across phases"""
        gap_skills = ["Python", "Django", "SQL", "Docker", "Kubernetes", "Terraform"]
        roadmap = fallback_roadmap(gap_skills)

        all_items = (
            roadmap["30_days"] +
            roadmap["60_days"] +
            roadmap["90_days"]
        )
        all_text = " ".join(all_items)

        for skill in gap_skills:
            self.assertIn(skill, all_text)

    def test_fallback_roadmap_empty_gap(self):
        """Fallback roadmap with no gaps should still return valid structure"""
        roadmap = fallback_roadmap([])
        self.assertIn("30_days", roadmap)
        self.assertIn("60_days", roadmap)
        self.assertIn("90_days", roadmap)
        self.assertIsInstance(roadmap["30_days"], list)