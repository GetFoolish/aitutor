#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import random
import time
from services.DashSystem.dash_system import DASHSystem, Question

def print_score_table(dash_system, student_id, current_time):
    """Print formatted score table for practiced skills only"""
    scores = dash_system.get_skill_scores(student_id, current_time)
    
    print("\n" + "="*120)
    print(f"{'SKILL SCORES FOR STUDENT: ' + student_id:^120}")
    print("="*120)
    print(f"{'Skill':<35} {'Grade':<8} {'Memory':<8} {'Prob':<8} {'Practice':<9} {'Correct':<8} {'Accuracy':<8}")
    print("-"*120)
    
    for _, data in scores.items():
        if data['practice_count'] > 0:  # Only show practiced skills
            print(f"{data['name']:<35} {data['grade_level']:<8} {data['memory_strength']:<8.3f} "
                  f"{data['probability']:<8.3f} {data['practice_count']:<9} {data['correct_count']:<8} {data['accuracy']:<8.3f}")
    
    print("-"*120)

def print_full_score_table(dash_system, student_id, current_time):
    """Print formatted score table for ALL skills"""
    scores = dash_system.get_skill_scores(student_id, current_time)
    
    print("\n" + "="*120)
    print(f"{'FULL SKILL SCORES FOR STUDENT: ' + student_id:^120}")
    print("="*120)
    print(f"{'Skill':<35} {'Grade':<8} {'Memory':<8} {'Prob':<8} {'Practice':<9} {'Correct':<8} {'Accuracy':<8}")
    print("-"*120)
    
    # Sort by grade level for better organization
    sorted_skills = sorted(scores.items(), key=lambda x: (x[1]['grade_level'], x[1]['name']))
    
    for _, data in sorted_skills:
        print(f"{data['name']:<35} {data['grade_level']:<8} {data['memory_strength']:<8.3f} "
              f"{data['probability']:<8.3f} {data['practice_count']:<9} {data['correct_count']:<8} {data['accuracy']:<8.3f}")
    
    print("-"*120)

def main():
    print("🎓 DASH Knowledge Tracing System Test")
    print("=====================================")
    
    # Initialize system
    dash_system = DASHSystem()
    
    # Get student ID
    student_id = "test_student"
    print(f"Using default student ID: {student_id}")
    
    # Load or create user profile
    user_profile = dash_system.load_user_or_create(student_id)
    
    print(f"\nStarting test session for student: {student_id}")
    
    # Show user stats
    stats = dash_system.user_manager.get_user_stats(user_profile)
    print(f"📊 User Stats: {stats['total_questions']} questions answered, {stats['accuracy']:.1%} accuracy")
    print(f"🎯 Skills practiced: {stats['skills_practiced']}/{len(dash_system.skills)}")
    
    print("You will be asked questions based on your skill level. Answer Y for correct, N for incorrect.")
    print("Press 'q' to quit at any time.\n")
    
    # Show initial state
    current_time = time.time()
    print("CURRENT STATE:")
    print_full_score_table(dash_system, student_id, current_time)
    
    question_count = 0
    max_questions = 20  # Limit the number of questions to prevent hanging
    
    for _ in range(max_questions):
        # Get the next recommended question
        question = dash_system.get_next_question(student_id, time.time())
        
        if not question:
            print("\n🎉 Congratulations! You've mastered all the available skills for now or no new questions could be generated.")
            break
            
        # Get skills associated with this question
        skill_names = [dash_system.skills[skill_id].name for skill_id in question.skill_ids]
        
        question_count += 1
        print(f"\n🔢 Question {question_count}")
        print(f"Skills tested: {', '.join(skill_names)}")
        print(f"Question: {question.content}")
        
        # Get user input
        response = input("Did the student answer correctly? (Y/N/q to quit): ")
        
        if response.lower() == 'q':
            break
        
        # Simulate response time (for testing time penalty)
        response_time = random.uniform(30, 300)  # 30 seconds to 5 minutes
        time_penalty = dash_system.calculate_time_penalty(response_time)
        time_status = "⚠️ SLOW" if time_penalty < 1.0 else "✅ FAST"
        
        print(f"⏱️  Response time: {response_time:.1f} seconds ({time_status})")
        if time_penalty < 1.0:
            print(f"   Time penalty applied: {time_penalty}x reward")
        
        is_correct = response == 'Y'
        current_time = time.time()
        
        # Store previous scores for comparison
        prev_scores = dash_system.get_skill_scores(student_id, current_time)
        
        # Record question attempt and update all states
        affected_skills = dash_system.record_question_attempt(
            user_profile, question.question_id, question.skill_ids, is_correct, response_time
        )
        
        # Get new scores
        new_scores = dash_system.get_skill_scores(student_id, current_time)
        
        # Show before/after comparison for all affected skills
        print(f"\n📊 SCORE CHANGES:")
        print(f"{'Skill':<25} {'Type':<12} {'Previous':<10} {'New':<10} {'Change':<10}")
        print("-"*70)
        
        for skill_id in affected_skills:
            skill_name = dash_system.skills[skill_id].name
            prev_prob = prev_scores[skill_id]['probability']
            new_prob = new_scores[skill_id]['probability']
            change = new_prob - prev_prob
            change_str = f"{change:+.3f}"
            
            # Determine if this is a direct skill or prerequisite
            skill_type = "Direct" if skill_id in question.skill_ids else "Prerequisite"
            
            print(f"{skill_name:<25} {skill_type:<12} {prev_prob:<10.3f} {new_prob:<10.3f} {change_str:<10}")
        
        # Show full score table every 3 questions
        if question_count % 3 == 0:
            print_score_table(dash_system, student_id, current_time)
        
        # Show recommendations
        recommendations = dash_system.get_recommended_skills(student_id, current_time)
        if recommendations:
            rec_names = [dash_system.skills[skill_id].name for skill_id in recommendations[:5]]
            print(f"\n💡 Recommended skills to practice: {', '.join(rec_names)}")
    
    # Final summary
    print(f"\n🎯 FINAL SUMMARY after {question_count} questions:")
    print_full_score_table(dash_system, student_id, current_time)
    
    # Show updated user stats
    final_stats = dash_system.user_manager.get_user_stats(user_profile)
    print(f"\n📈 SESSION RESULTS:")
    print(f"  Total questions ever: {final_stats['total_questions']}")
    print(f"  Overall accuracy: {final_stats['accuracy']:.1%}")
    print(f"  Average response time: {final_stats['avg_response_time']:.1f}s")
    print(f"  Time penalties: {final_stats['time_penalties']}")
    print(f"  Skills practiced: {final_stats['skills_practiced']}/{len(dash_system.skills)}")
    
    recommendations = dash_system.get_recommended_skills(student_id, current_time)
    if recommendations:
        print(f"\n💡 Skills needing practice:")
        for skill_id in recommendations[:10]:
            skill_name = dash_system.skills[skill_id].name
            prob = dash_system.predict_correctness(student_id, skill_id, current_time)
            print(f"  - {skill_name}: {prob:.3f} probability")
    
    print(f"\n💾 User data saved to: Users/{student_id}.json")
    print(f"Test session completed for {student_id}!")

if __name__ == "__main__":
    main()
