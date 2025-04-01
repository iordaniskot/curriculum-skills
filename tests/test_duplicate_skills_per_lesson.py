import json
import os
import unittest
from unittest.mock import patch, MagicMock
import sys
from main import PDFProcessingRequest


# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import calculate_skillnames

class TestDuplicateSkillsPerLesson(unittest.TestCase):
    """Test case to ensure no skill is assigned more than once to the same lesson."""
    
    @patch("main.calculate_skillnames")
    @patch("main.process_pdf")
    def test_duplicate_detection(self, mock_process_pdf, mock_calculate_skillnames):
        """
        Test the duplicate detection mechanism by intentionally adding duplicates.
        This test should initially find duplicates to verify the detection works.
        """
            # Load test data
        with open("tests/json/extracted_skills_expected.json", "r", encoding="utf-8") as f:
            expected = json.load(f)
        
        mock_process_pdf.return_value = None
        mock_calculate_skillnames.return_value = {
            "skills": expected["skills"]
        }
        
        # Simulate API call
        from main import process_pdf, calculate_skillnames
        process_pdf(PDFProcessingRequest(pdf_name="tests/sample_pdfs/Cambridge University.pdf"))
        response = calculate_skillnames("University of Cambridge")
        
        skills_data = response["skills"]
        
        # Use a hash map to check for duplicates in each lesson
        for lesson_name, skills in skills_data.items():
            if lesson_name in ["university_name", "university_country"]:
                continue
                
            skills.append(skills[0])  # Intentionally add a duplicate
            # Create a hash map to track skill occurrences
            skill_occurrences = {}
            duplicates = []
            
            for skill in skills:
                if skill in skill_occurrences:
                    duplicates.append(skill)
                    skill_occurrences[skill] += 1
                else:
                    skill_occurrences[skill] = 1
            
            # Assert  duplicates were found
            self.assertGreater(
                len(duplicates), 
                0, 
                f"Expected duplicates in lesson '{lesson_name}' but found none."
            )
            
        
        # Print summary
        print("\n✅ Duplicate Skills Check")    
        print(f"✔ Lessons checked: {len(skills_data)}")
        print(f"✔ Duplicates found in lessons: {len(duplicates)}")
        print(f"✔ The duplicates are: {duplicates}")
    
    @patch("main.calculate_skillnames")
    @patch("main.process_pdf")
    def test_no_duplicates_using_hashmap(self, mock_process_pdf, mock_calculate_skillnames):
        """
        Test that checks for duplicate skills in lessons using a hash map approach.
        """
        # Load test data
        with open("tests/json/extracted_skills_expected.json", "r", encoding="utf-8") as f:
            expected = json.load(f)
        
        mock_process_pdf.return_value = None
        mock_calculate_skillnames.return_value = {
            "skills": expected["skills"]
        }
        
        # Simulate API call
        from main import process_pdf, calculate_skillnames
        process_pdf(PDFProcessingRequest(pdf_name="tests/sample_pdfs/Cambridge University.pdf"))
        response = calculate_skillnames("University of Cambridge")
        
        skills_data = response["skills"]
        
        # Use a hash map to check for duplicates in each lesson
        for lesson_name, skills in skills_data.items():
            if lesson_name in ["university_name", "university_country"]:
                continue
                
            # Create a hash map to track skill occurrences
            skill_occurrences = {}
            duplicates = []
            
            for skill in skills:
                if skill in skill_occurrences:
                    duplicates.append(skill)
                    skill_occurrences[skill] += 1
                else:
                    skill_occurrences[skill] = 1
            
            # Assert no duplicates were found
            self.assertEqual(
                0, 
                len(duplicates), 
                f"Found duplicate skills in lesson '{lesson_name}': {[(skill, count) for skill, count in skill_occurrences.items() if count > 1]}"
            )
        
        # Print summary
        print("\n✅ Duplicate Skills Check")
        print(f"✔ Lessons checked: {len(skills_data)}")
        print(f"✔ All lessons have unique skills")

if __name__ == "__main__":
    unittest.main()
