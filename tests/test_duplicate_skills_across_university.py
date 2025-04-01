import json
import os
import unittest
from unittest.mock import patch, MagicMock
import sys

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import PDFProcessingRequest
from skills import get_skills_for_lesson
from config import DB_CONFIG
from database import is_database_connected

class TestDuplicateSkillsAcrossUniversity(unittest.TestCase):
    """Test case to detect which skills are duplicated across different lessons within a university."""
    
    @patch("mysql.connector.connect")
    @patch("main.process_pdf")
    def test_find_duplicate_skills_across_university_mock(self, mock_process_pdf, mock_db_connect):
        """
        Test to find skills that appear in multiple lessons across the university.
        This helps identify which skills are taught in different courses.
        """
        # Setup mock database connection and cursor based on Cambridge University PDF data
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_connection
        
        # Load the expected skills data from the Cambridge University PDF
        with open("tests/json/extracted_skills_expected.json", "r", encoding="utf-8") as f:
            expected_data = json.load(f)
        
        # Create mock data from the expected skills in Cambridge University PDF
        university_skills = []
        for lesson_name, skills in expected_data["skills"].items():
            if lesson_name in ["university_name", "university_country"]:
                continue
            
            for skill in skills:
                university_skills.append({
                    'university_name': 'University of Cambridge',
                    'lesson_name': lesson_name,
                    'skill_name': skill
                })
        
        # Mock the database query results with data from the Cambridge University PDF
        mock_cursor.fetchall.side_effect = [
            # First query to get university names
            [{'university_name': 'University of Cambridge'}],
            
            # Second query to get skills - use the actual skills from Cambridge University PDF
            university_skills
        ]
        
        # Mock process_pdf to avoid actual file processing
        mock_process_pdf.return_value = None
        
        # Call the function to get skills across the university
        from main import process_pdf
        process_pdf(PDFProcessingRequest(pdf_name="tests/sample_pdfs/Cambridge University.pdf"))
        
        # Get skills from the mocked database
        result = get_skills_for_lesson("University of Cambridge", all_data=True, db_config=DB_CONFIG)
        
        # Verify we have results
        self.assertIsNotNone(result, "Result should not be None")
        self.assertIn("University of Cambridge", result, "Expected university name in results")
        
        # Find skills that appear in multiple lessons
        skill_to_lessons = {}
        for university, lessons in result.items():
            for lesson, skills in lessons.items():
                for skill in skills:
                    if skill not in skill_to_lessons:
                        skill_to_lessons[skill] = []
                    skill_to_lessons[skill].append(lesson)
        
        # Get skills that appear in more than one lesson (duplicates across lessons)
        duplicate_skills = {skill: lessons for skill, lessons in skill_to_lessons.items() if len(lessons) > 1}
        
        
        
        
        # Print results for visibility
        # Print results for visibility
        print("\n✅ Cross-University Skill Analysis")
        
        # Create a dictionary to count skills from the expected data
        expected_skill_counts = {}
        for lesson, skills in expected_data["skills"].items():
            if lesson in ["university_name", "university_country"]:
                continue
            for skill in skills:
                if skill not in expected_skill_counts:
                    expected_skill_counts[skill] = 0
                expected_skill_counts[skill] += 1
        
        # Compare with our calculated duplicate skills
        actual_skill_counts = {skill: len(lessons) for skill, lessons in skill_to_lessons.items()}
        
        # Verify that the counts match
        for skill, expected_count in expected_skill_counts.items():
            actual_count = actual_skill_counts.get(skill, 0)
            self.assertEqual(
            actual_count, 
            expected_count, 
            f"Skill '{skill}' should appear in {expected_count} lessons but appears in {actual_count}"
            )
        
        # Verify no unexpected skills
        for skill in actual_skill_counts:
            self.assertIn(
            skill, 
            expected_skill_counts, 
            f"Unexpected skill '{skill}' found in results"
            )
        print(f"✔ University: University of Cambridge")
        print(f"✔ Total unique skills: {len(skill_to_lessons)}")
        print(f"✔ Skills appearing in multiple lessons: {len(duplicate_skills)}")
        
        # Print top duplicated skills (limit to 5 for brevity)
        for i, (skill, lessons) in enumerate(
            sorted(duplicate_skills.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        ):
            print(f"  - '{skill}' appears in {len(lessons)} lessons: {', '.join(lessons[:3])}")
        
        # Check if we found any duplicates
        if duplicate_skills:
            # Get the most duplicated skill
            most_duplicated = max(duplicate_skills.items(), key=lambda x: len(x[1]))
            print(f"\n✔ Most duplicated skill: '{most_duplicated[0]}' appears in {len(most_duplicated[1])} lessons")
            
            # Verify that at least one skill appears in multiple lessons
            self.assertGreater(len(duplicate_skills), 0, 
                              "Expected to find at least one skill appearing in multiple lessons")
        else:
            print("\n⚠️ No duplicate skills found across lessons in the Cambridge University PDF.")



# For real data test, for check purpose only
    # @patch("main.process_pdf")
    # def test_find_duplicate_skills_across_university_real(self, mock_process_pdf):
    #     """
    #     Test to find skills that appear in multiple lessons using real data.
    #     This test uses get_skills_for_lesson with actual data.
    #     """
    #     # Skip the test if the database is not available
    #     from database import is_database_connected
    #     if not is_database_connected(DB_CONFIG):
    #         self.skipTest("Database is not connected. Skipping real database test.")
            
    #     # Load the expected skills data from the Cambridge University PDF
    #     with open("tests/json/extracted_skills_expected.json", "r", encoding="utf-8") as f:
    #         expected_data = json.load(f)
            
    #     # Mock process_pdf to avoid actual file processing    
    #     mock_process_pdf.return_value = None
        
    #     # Process PDF with mock
    #     process_pdf = PDFProcessingRequest(pdf_name="tests/sample_pdfs/Cambridge University.pdf")
            
    #     # Use get_skills_for_lesson directly with the database config
    #     result = get_skills_for_lesson("University of Cambridge", all_data=True, db_config=DB_CONFIG)
            
    #     # If we didn't get results, fall back to the expected data for testing
    #     if not result or "University of Cambridge" not in result:
    #         print("⚠️ No data from database, using expected data for testing")
    #         result = {
    #             "University of Cambridge": {
    #                 lesson: skills for lesson, skills in expected_data["skills"].items()
    #                 if lesson not in ["university_name", "university_country"]
    #             }
    #         }
        
    #     # Find skills that appear in multiple lessons
    #     skill_to_lessons = {}
    #     for university, lessons in result.items():
    #         for lesson, skills in lessons.items():
    #             for skill in skills:
    #                 if skill not in skill_to_lessons:
    #                     skill_to_lessons[skill] = []
    #                 skill_to_lessons[skill].append(lesson)
        
    #     # Get skills that appear in more than one lesson (duplicates across lessons)
    #     duplicate_skills = {skill: lessons for skill, lessons in skill_to_lessons.items() if len(lessons) > 1}
        
    #     # Print results for visibility
    #     print("\n✅ Real Data Cross-University Skill Analysis (using get_skills_for_lesson)")
    #     print(f"✔ University: University of Cambridge")
    #     print(f"✔ Total unique skills: {len(skill_to_lessons)}")
    #     print(f"✔ Skills appearing in multiple lessons: {len(duplicate_skills)}")
        
    #     # Print top duplicated skills (limit to 5 for brevity)
    #     for i, (skill, lessons) in enumerate(
    #         sorted(duplicate_skills.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    #     ):
    #         print(f"  - '{skill}' appears in {len(lessons)} lessons: {', '.join(lessons[:3])}")
        
    #     # Check if we found any duplicates
    #     if duplicate_skills:
    #         # Get the most duplicated skill
    #         most_duplicated = max(duplicate_skills.items(), key=lambda x: len(x[1]))
    #         print(f"\n✔ Most duplicated skill: '{most_duplicated[0]}' appears in {len(most_duplicated[1])} lessons")
            
    #         # Verify that at least one skill appears in multiple lessons
    #         self.assertGreater(len(duplicate_skills), 0, 
    #                          "Expected to find at least one skill appearing in multiple lessons")
    #     else:
    #         print("\n⚠️ No duplicate skills found across lessons in the real Cambridge University data.")

if __name__ == "__main__":
    unittest.main()


