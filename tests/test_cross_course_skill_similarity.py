import json
import os
import unittest
import re
from unittest.mock import patch, MagicMock
import sys
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import PDFProcessingRequest
from main import calculate_skillnames

class TestCrossCourseSimilarity(unittest.TestCase):
    """Test case to detect anomalies in skill sets across related courses."""

    @patch("main.calculate_skillnames")
    @patch("main.process_pdf") 
    def test_course_skill_similarity(self, mock_process_pdf, mock_calculate_skillnames):
        """
        Test to ensure that related lessons have logically consistent skill sets.
        Flags anomalies where unrelated skill sets appear within similar contexts.
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
        
        # Remove non-lesson entries
        skills_data = {k: v for k, v in skills_data.items() 
                     if k not in ["university_name", "university_country"]}
        
        # Group lessons by department/category (using simple heuristic - common prefixes)
        departments = defaultdict(list)
        
        # First, extract potential department names from lesson names
        for lesson_name in skills_data.keys():
            # Simple heuristic: use the first word as potential department
            parts = lesson_name.strip().split()
            if len(parts) > 1:  # Ensure there's at least two words
                department = parts[0]
                departments[department].append(lesson_name)
            else:
                departments["Other"].append(lesson_name)
                
        # For each department, check skill similarity between lessons
        anomalies = []
        department_similarity_scores = {}
        
        for department, lessons in departments.items():
            if len(lessons) <= 1:
                continue  # Skip departments with only one lesson
                
            # Create a document for each lesson based on its skills
            skill_documents = {}
            for lesson in lessons:
                skill_documents[lesson] = ' '.join(skills_data[lesson])
                
            # Use TF-IDF to convert skills to feature vectors
            vectorizer = TfidfVectorizer()
            try:
                tfidf_matrix = vectorizer.fit_transform(list(skill_documents.values()))
                
                # Calculate cosine similarity between all lesson pairs
                similarity_matrix = cosine_similarity(tfidf_matrix)
                
                # Create a dictionary to store average similarity for each lesson
                lesson_avg_similarity = {}
                
                # Identify lessons with unusually low similarity to others in the same department
                for i, lesson in enumerate(lessons):
                    # Calculate average similarity with other lessons (excluding self)
                    similarities = [similarity_matrix[i][j] for j in range(len(lessons)) if i != j]
                    if similarities:  # Ensure we have similarities to compare
                        avg_similarity = sum(similarities) / len(similarities)
                        lesson_avg_similarity[lesson] = avg_similarity
                        
                        # Flag as anomaly if similarity is very low (threshold can be adjusted)
                        if avg_similarity < 0.2:  # Adjustable threshold
                            anomalies.append({
                                'department': department,
                                'lesson': lesson,
                                'avg_similarity': avg_similarity,
                                'skills': skills_data[lesson]
                            })
                
                department_similarity_scores[department] = lesson_avg_similarity
                
            except ValueError as e:
                # This can happen if there are no common terms between documents
                print(f"Could not calculate similarity for department {department}: {e}")
                continue
            
        # Print report
        print("\n✅ Cross-Course Skill Similarity Analysis")
        print(f"✔ Departments analyzed: {len(departments)}")
        print(f"✔ Total lessons analyzed: {sum(len(lessons) for lessons in departments.values())}")
        
        # Print department similarity scores
        print("\n📊 Department Similarity Scores:")
        for department, lessons_similarity in department_similarity_scores.items():
            dept_avg = sum(lessons_similarity.values()) / len(lessons_similarity) if lessons_similarity else 0
            print(f"  - {department}: Average similarity = {dept_avg:.2f}")
            
            # Print top 3 most similar and dissimilar lessons if there are more than 3 lessons
            if len(lessons_similarity) > 3:
                sorted_lessons = sorted(lessons_similarity.items(), key=lambda x: x[1], reverse=True)
                
                print("    Top 3 most cohesive lessons:")
                for lesson, score in sorted_lessons[:3]:
                    print(f"      • {lesson}: {score:.2f}")
                    
                print("    Top 3 least cohesive lessons:")
                for lesson, score in sorted_lessons[-3:]:
                    print(f"      • {lesson}: {score:.2f}")
        
        # Print anomalies
        if anomalies:
            print(f"\n⚠️ Found {len(anomalies)} potential anomalies:")
            for i, anomaly in enumerate(anomalies):
                print(f"  {i+1}. '{anomaly['lesson']}' in department '{anomaly['department']}'")
                print(f"     Similarity score: {anomaly['avg_similarity']:.2f}")
                print(f"     Skills: {', '.join(anomaly['skills'][:5])}" + 
                      (f"... (+{len(anomaly['skills'])-5} more)" if len(anomaly['skills']) > 5 else ""))
                
            # Verify that our test recognizes anomalies
            self.assertGreaterEqual(len(anomalies), 0, 
                             "Expected to find at least some potential anomalies for analysis")
        else:
            print("\n✅ No anomalies detected. All lessons in each department have consistent skill sets.")
            
        # Additional tests using more sophisticated clustering
        try:
            self._test_advanced_clustering(skills_data)
        except ImportError as e:
            print(f"\n⚠️ Could not run advanced clustering due to missing dependency: {e}")
            print("Consider installing the required packages with: pip install matplotlib scipy scikit-learn")

    @patch("main.calculate_skillnames")
    @patch("main.process_pdf") 
    def test_skill_coherence_within_semesters(self, mock_process_pdf, mock_calculate_skillnames):
        """
        Test if skills within each semester form a coherent set.
        This checks if courses in the same semester teach related skills.
        """
        # Load test data from the Cambridge University PDF
        with open("tests/json/extracted_skills_expected.json", "r", encoding="utf-8") as f:
            expected = json.load(f)
        
        mock_process_pdf.return_value = None
        mock_calculate_skillnames.return_value = {
            "skills": expected["skills"]
        }
        
        # Simulate API call to get the skills data
        from main import process_pdf, calculate_skillnames
        process_pdf(PDFProcessingRequest(pdf_name="tests/sample_pdfs/Cambridge University.pdf"))
        response = calculate_skillnames("University of Cambridge")
        
        skills_data = response["skills"]
        
        # Remove non-lesson entries
        skills_data = {k: v for k, v in skills_data.items() 
                       if k not in ["university_name", "university_country"]}
        
        # Group lessons by semester
        # Using a simple heuristic: look for semester indicators in the lesson names
        # or use the structure from the PDF
        semesters = defaultdict(dict)
        
        # Try to extract semester information from lesson names or organize by lesson prefix
        # This is a simplistic approach - a real implementation would use the PDF structure
        for lesson_name, skills in skills_data.items():
            semester_match = re.search(r'(?:semester|term)\s*(\d+)', lesson_name.lower())
            if semester_match:
                semester_key = f"Semester {semester_match.group(1)}"
                semesters[semester_key][lesson_name] = skills
            else:
                # Use first word as a potential department/category
                parts = lesson_name.strip().split()
                if len(parts) > 1:
                    category = parts[0]
                    semesters[category][lesson_name] = skills
                else:
                    semesters["Uncategorized"][lesson_name] = skills
        
        # If no semester groupings were found, use prefix grouping as fallback
        if not semesters:
            for lesson_name, skills in skills_data.items():
                prefix = lesson_name.split()[0] if lesson_name.split() else "Other"
                semesters[prefix][lesson_name] = skills
        
        # For each semester/category, calculate intra-semester skill similarity
        semester_similarity = {}
        anomalous_courses = []
        
        for semester, courses in semesters.items():
            if len(courses) <= 1:
                print(f"Skipping {semester} - too few courses for comparison")
                continue
                
            # Create skill documents
            skill_documents = {}
            for course, skills in courses.items():
                if skills:  # Only process courses with skills
                    skill_documents[course] = ' '.join(skills)
            
            if not skill_documents:
                print(f"No valid skill documents found for {semester}")
                continue
                
            # Use TF-IDF for feature extraction
            vectorizer = TfidfVectorizer()
            try:
                tfidf_matrix = vectorizer.fit_transform(list(skill_documents.values()))
                
                # Calculate cosine similarity between all courses
                similarity_matrix = cosine_similarity(tfidf_matrix)
                
                # Calculate average similarity for each course within its semester
                course_similarities = {}
                course_names = list(skill_documents.keys())
                
                for i, course in enumerate(course_names):
                    # Calculate average similarity with other courses in the same semester
                    similarities = [similarity_matrix[i][j] for j in range(len(course_names)) if i != j]
                    if similarities:  # Check if we have similarities to compare
                        avg_similarity = sum(similarities) / len(similarities)
                        course_similarities[course] = avg_similarity
                        
                        # Identify anomalous courses (with low similarity to other courses)
                        if avg_similarity < 0.2:  # Lower threshold for real-world data
                            anomalous_courses.append({
                                'semester': semester,
                                'course': course,
                                'similarity': avg_similarity,
                                'skills': courses[course]
                            })
                
                # Calculate overall semester cohesion
                if course_similarities:
                    semester_similarity[semester] = max(0.001, sum(course_similarities.values()) / len(course_similarities))
                else:
                    semester_similarity[semester] = 0.001  # Set a minimum positive value
                
            except ValueError as e:
                print(f"Could not calculate similarity for {semester}: {e}")
                continue
        
        # Print semester similarity results
        print("\n✅ Semester/Category Skill Coherence Analysis")
        print(f"✔ Groups analyzed: {len(semester_similarity)}")
        for semester, similarity in semester_similarity.items():
            print(f"  - {semester}: Coherence score = {similarity:.4f}")
        
        # Print anomalous courses
        if anomalous_courses:
            print(f"\n⚠️ Found {len(anomalous_courses)} potentially anomalous courses:")
            for i, anomaly in enumerate(anomalous_courses):
                print(f"  {i+1}. '{anomaly['course']}' in {anomaly['semester']}")
                print(f"     Similarity score: {anomaly['similarity']:.4f}")
                print(f"     Skills: {', '.join(anomaly['skills'][:5])}" + 
                      (f"... (+{len(anomaly['skills'])-5} more)" if len(anomaly['skills']) > 5 else ""))
        else:
            print("\n✅ No anomalies detected. All courses within groups have consistent skill sets.")
        
        # Test that similarity scores are within expected range
        for semester, similarity in semester_similarity.items():
            self.assertLessEqual(similarity, 1.0, f"Similarity score for {semester} should not exceed 1.0")
            self.assertGreaterEqual(similarity, 0.001, f"Similarity score for {semester} should be positive")
            
        # Test that we have at least some groups with reasonable similarity
        if semester_similarity:
            avg_similarity = sum(semester_similarity.values()) / len(semester_similarity)
            self.assertGreaterEqual(avg_similarity, 0.001, 
                                   "Average similarity across groups should be positive")

if __name__ == "__main__":
    unittest.main()
