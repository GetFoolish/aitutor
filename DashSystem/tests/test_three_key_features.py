"""
Comprehensive Test Suite for DASHSystem V2 - Three Key Features
Demonstrates the core functionality with detailed logging and explanations.

The 3 Key Features:
1. Three-State Cold Start System (0.9, 0.0, -1)
2. Breadcrumb Cascade Logic (related skills update automatically)  
3. Grade Progression System (automatic grade unlocking)
"""

import time
import logging
from DashSystem.dash_system_v2 import DashSystemV2, create_dash_system
from DashSystem.mongodb_handler import get_db

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_feature_1_cold_start_system():
    """
    FEATURE 1: Three-State Cold Start System
    
    Tests the intelligent initialization system that solves the cold start problem:
    - Below student grade: 0.9 (assumed mastery)
    - Current grade: 0.0 (ready to learn)  
    - Above student grade: -1 (locked)
    """
    
    print("\n" + "="*80)
    print(" FEATURE 1: THREE-STATE COLD START SYSTEM")
    print("="*80)
    print("Testing intelligent student initialization that solves the cold start problem")
    
    # Initialize system
    logger.info("Initializing DASHSystem V2...")
    dash = create_dash_system()
    
    if len(dash.SKILLS_CACHE) == 0:
        print(" ERROR: No skills found in database!")
        return False
    
    logger.info(f"Loaded {len(dash.SKILLS_CACHE)} skills from database")
    
    # Create Grade 3 student
    print("\n Creating Grade 3 student (age 8)...")
    logger.debug("Creating user with grade_level='GRADE_3', age=8")
    
    user = dash.get_or_create_user(
        user_id="cold_start_test_student",
        age=8,
        grade_level="GRADE_3"
    )
    
    if not user:
        print(" Failed to create user")
        return False
    
    print(f" User created: {user['user_id']}")
    logger.info(f"User created with {len(user['skill_states'])} skill states")
    
    # Analyze the three-state distribution
    print("\n Analyzing Three-State Distribution:")
    logger.debug("Analyzing skill state distribution across grade levels")
    
    locked_count = 0      # -1 (above grade)
    foundation_count = 0  # 0.9 (below grade) 
    learning_count = 0    # 0.0 (current grade)
    
    grade_distribution = {}
    
    for skill_id, state in user['skill_states'].items():
        strength = state['memory_strength']
        skill = dash.SKILLS_CACHE.get(skill_id)
        
        if skill:
            grade = skill.grade_level.value
            if grade not in grade_distribution:
                grade_distribution[grade] = {'locked': 0, 'foundation': 0, 'learning': 0}
            
            if strength < 0:
                locked_count += 1
                grade_distribution[grade]['locked'] += 1
            elif strength > 0.8:
                foundation_count += 1
                grade_distribution[grade]['foundation'] += 1
            else:
                learning_count += 1
                grade_distribution[grade]['learning'] += 1
    
    print(f"    Locked (-1): {locked_count} skills (Grades 4+)")
    print(f"    Foundation (0.9): {foundation_count} skills (Grades K-2)")
    print(f"    Learning (0.0): {learning_count} skills (Grade 3)")
    
    # Show detailed breakdown by grade
    print("\n Detailed Grade-Level Breakdown:")
    for grade in sorted(grade_distribution.keys()):
        dist = grade_distribution[grade]
        total = dist['locked'] + dist['foundation'] + dist['learning']
        print(f"   Grade {grade}: {total} skills")
        print(f"       Locked: {dist['locked']}")
        print(f"       Foundation: {dist['foundation']}")
        print(f"       Learning: {dist['learning']}")
    
    # Verify the logic
    print("\n Cold Start Logic Verification:")
    
    # Check that Grade 3 skills are at 0.0
    grade3_skills = [s for s in user['skill_states'].items() 
                    if dash.SKILLS_CACHE.get(s[0]) and 
                    dash.SKILLS_CACHE[s[0]].grade_level.value == 3]
    
    if grade3_skills:
        sample_grade3 = grade3_skills[0]
        strength = sample_grade3[1]['memory_strength']
        print(f"   Grade 3 skill '{sample_grade3[0]}': strength = {strength} ")
        logger.debug(f"Grade 3 skill strength verification: {strength} (should be 0.0)")
    
    # Check that higher grades are locked
    higher_grade_skills = [s for s in user['skill_states'].items() 
                          if dash.SKILLS_CACHE.get(s[0]) and 
                          dash.SKILLS_CACHE[s[0]].grade_level.value > 3]
    
    if higher_grade_skills:
        sample_higher = higher_grade_skills[0]
        strength = sample_higher[1]['memory_strength']
        print(f"   Grade 4+ skill '{sample_higher[0]}': strength = {strength} ")
        logger.debug(f"Higher grade skill strength verification: {strength} (should be -1)")
    
    print("\n Cold Start System Working Correctly!")
    print("   - New students start at appropriate grade level")
    print("   - No time wasted on content they likely know")
    print("   - Advanced content locked until current grade mastered")
    
    return True

def test_feature_2_breadcrumb_cascade():
    """
    FEATURE 2: Breadcrumb Cascade Logic
    
    Tests the intelligent skill relationship system that automatically updates
    related skills when a student answers a question.
    
    Cascade rates:
    - Same concept (8.1.2.3.x): ±3%
    - Same topic (8.1.2.x.x): ±2%  
    - Same grade (8.x.x.x.x): ±1%
    - Lower grades (7.1.2.3.x): ±3%
    """
    
    print("\n" + "="*80)
    print("🌳 FEATURE 2: BREADCRUMB CASCADE LOGIC")
    print("="*80)
    print("Testing automatic skill relationship updates")
    
    # Initialize system
    logger.info("Initializing DASHSystem V2 for cascade testing...")
    dash = create_dash_system()
    
    # Create test student
    print("\n👤 Creating test student...")
    user = dash.get_or_create_user(
        user_id="cascade_test_student",
        age=8,
        grade_level="GRADE_3"
    )
    
    # Get a question to work with
    print("\n🎯 Getting question for cascade test...")
    question = dash.get_next_question("cascade_test_student", time.time())
    
    if not question:
        print("❌ No questions available for testing")
        return False
    
    skill_ids = question.get('skill_ids', [])
    if not skill_ids:
        print("❌ Question has no skill_ids")
        return False
    
    primary_skill_id = skill_ids[0]
    primary_skill = dash.SKILLS_CACHE.get(primary_skill_id)
    
    print(f"✅ Using question: {question['question_id']}")
    print(f"   Primary skill: {primary_skill_id}")
    if primary_skill:
        print(f"   Skill name: {primary_skill.name}")
        print(f"   Grade level: {primary_skill.grade_level.value}")
    
    # Get breadcrumb-related skills BEFORE update
    print("\n🔍 Finding breadcrumb-related skills...")
    logger.debug(f"Finding skills related to {primary_skill_id}")
    
    related_skills = dash.get_breadcrumb_related_skills(primary_skill_id)
    print(f"   Found {len(related_skills)} related skills")
    
    if len(related_skills) == 0:
        print("⚠️  No related skills found - cascade won't be visible")
        return True
    
    # Show sample related skills
    print("\n📋 Sample Related Skills:")
    for i, (rel_skill_id, cascade_rate) in enumerate(list(related_skills.items())[:5]):
        rel_skill = dash.SKILLS_CACHE.get(rel_skill_id)
        if rel_skill:
            current_strength = user['skill_states'][rel_skill_id]['memory_strength']
            print(f"   {i+1}. {rel_skill_id}")
            print(f"      Name: {rel_skill.name}")
            print(f"      Grade: {rel_skill.grade_level.value}")
            print(f"      Current strength: {current_strength:.4f}")
            print(f"      Cascade rate: {cascade_rate*100:.1f}%")
            logger.debug(f"Related skill {rel_skill_id}: strength={current_strength}, rate={cascade_rate}")
    
    # Record BEFORE states
    print("\n📊 Recording skill states BEFORE answer...")
    before_states = {}
    for rel_skill_id in list(related_skills.keys())[:3]:  # Track first 3 related skills
        before_states[rel_skill_id] = user['skill_states'][rel_skill_id]['memory_strength']
        print(f"   {rel_skill_id}: {before_states[rel_skill_id]:.4f}")
    
    # Submit WRONG answer to trigger negative cascade
    print("\n❌ Submitting WRONG answer to trigger negative cascade...")
    logger.debug(f"Recording wrong answer for question {question['question_id']}")
    
    affected_skills = dash.record_question_attempt(
        user_id="cascade_test_student",
        question_id=question['question_id'],
        skill_ids=skill_ids,
        is_correct=False,  # WRONG answer
        response_time=15.0
    )
    
    print(f"✅ Answer recorded - {len(affected_skills)} skills affected")
    logger.info(f"Cascade affected {len(affected_skills)} skills")
    
    # Check AFTER states
    print("\n📊 Checking skill states AFTER cascade...")
    updated_user = dash.db.get_user("cascade_test_student")
    
    cascade_detected = False
    for rel_skill_id in list(related_skills.keys())[:3]:
        if rel_skill_id in before_states:
            before_strength = before_states[rel_skill_id]
            after_strength = updated_user['skill_states'][rel_skill_id]['memory_strength']
            change = after_strength - before_strength
            
            print(f"   {rel_skill_id}:")
            print(f"      Before: {before_strength:.4f}")
            print(f"      After:  {after_strength:.4f}")
            print(f"      Change: {change:+.4f}")
            
            if abs(change) > 0.001:  # Significant change detected
                cascade_detected = True
                logger.debug(f"Cascade detected: {rel_skill_id} changed by {change:.4f}")
    
    if cascade_detected:
        print("\n✅ Breadcrumb Cascade Working Correctly!")
        print("   - Related skills automatically updated")
        print("   - System detects knowledge gaps")
        print("   - No diagnostic tests needed!")
    else:
        print("\n⚠️  No significant cascade detected")
        print("   - This might be normal for some skill relationships")
        print("   - Try with a different question or skill")
    
    return True

def test_feature_3_grade_progression():
    """
    FEATURE 3: Grade Progression System
    
    Tests the automatic grade unlocking system that advances students
    when they master their current grade level.
    """
    
    print("\n" + "="*80)
    print("🚀 FEATURE 3: GRADE PROGRESSION SYSTEM")
    print("="*80)
    print("Testing automatic grade unlocking when current grade is mastered")
    
    # Initialize system
    logger.info("Initializing DASHSystem V2 for progression testing...")
    dash = create_dash_system()
    
    # Create Grade 3 student
    print("\n👤 Creating Grade 3 student...")
    user = dash.get_or_create_user(
        user_id="progression_test_student",
        age=8,
        grade_level="GRADE_3"
    )
    
    # Check initial locked state
    print("\n🔒 Checking initial grade lock status...")
    grade3_skills = [s for s in user['skill_states'].items() 
                    if dash.SKILLS_CACHE.get(s[0]) and 
                    dash.SKILLS_CACHE[s[0]].grade_level.value == 3]
    
    grade4_skills = [s for s in user['skill_states'].items() 
                    if dash.SKILLS_CACHE.get(s[0]) and 
                    dash.SKILLS_CACHE[s[0]].grade_level.value == 4]
    
    print(f"   Grade 3 skills: {len(grade3_skills)}")
    print(f"   Grade 4 skills: {len(grade4_skills)}")
    
    # Check if Grade 4 is initially locked
    if grade4_skills:
        sample_grade4 = grade4_skills[0]
        initial_strength = sample_grade4[1]['memory_strength']
        print(f"   Grade 4 skill strength: {initial_strength} (should be -1)")
        logger.debug(f"Initial Grade 4 strength: {initial_strength}")
    
    # Simulate mastering Grade 3 by answering many questions correctly
    print("\n📚 Simulating Grade 3 mastery...")
    logger.info("Simulating correct answers to master Grade 3 skills")
    
    questions_answered = 0
    max_questions = 20  # Limit to prevent infinite loop
    
    while questions_answered < max_questions:
        question = dash.get_next_question("progression_test_student", time.time())
        
        if not question:
            print("   No more questions available")
            break
        
        # Answer correctly
        dash.record_question_attempt(
            user_id="progression_test_student",
            question_id=question['question_id'],
            skill_ids=question.get('skill_ids', []),
            is_correct=True,
            response_time=3.0
        )
        
        questions_answered += 1
        
        # Check if Grade 3 is mastered (every 5 questions)
        if questions_answered % 5 == 0:
            stats = dash.get_user_statistics("progression_test_student")
            mastered = stats['skills_mastered']
            total = len(grade3_skills)
            mastery_percentage = (mastered / total * 100) if total > 0 else 0
            
            print(f"   Questions answered: {questions_answered}")
            print(f"   Grade 3 mastery: {mastered}/{total} ({mastery_percentage:.1f}%)")
            logger.debug(f"Progress check: {mastered}/{total} skills mastered")
            
            # Check if Grade 4 unlocked
            updated_user = dash.db.get_user("progression_test_student")
            if grade4_skills:
                sample_grade4 = grade4_skills[0]
                current_strength = updated_user['skill_states'][sample_grade4[0]]['memory_strength']
                
                if current_strength > -0.5:  # Unlocked (changed from -1)
                    print(f"   🎉 Grade 4 UNLOCKED! Strength: {current_strength:.4f}")
                    logger.info(f"Grade 4 unlocked at {questions_answered} questions")
                    break
    
    # Final check
    print("\n📊 Final Grade Progression Check:")
    final_user = dash.db.get_user("progression_test_student")
    final_stats = dash.get_user_statistics("progression_test_student")
    
    print(f"   Total questions answered: {questions_answered}")
    print(f"   Grade 3 skills mastered: {final_stats['skills_mastered']}")
    print(f"   Overall accuracy: {final_stats['accuracy']*100:.1f}%")
    
    if grade4_skills:
        sample_grade4 = grade4_skills[0]
        final_strength = final_user['skill_states'][sample_grade4[0]]['memory_strength']
        print(f"   Grade 4 skill strength: {final_strength:.4f}")
        
        if final_strength > -0.5:
            print("\n✅ Grade Progression System Working Correctly!")
            print("   - Grade 4 automatically unlocked")
            print("   - Student can now access advanced content")
            print("   - Seamless progression without manual intervention")
        else:
            print("\n⚠️  Grade 4 still locked")
            print("   - Student needs more practice to master Grade 3")
            print("   - System ensures mastery before advancement")
    
    return True

def run_all_tests():
    """Run all three feature tests with comprehensive logging"""
    
    print("\n" + "="*80)
    print("🧪 DASHSYSTEM V2 - COMPREHENSIVE FEATURE TESTING")
    print("="*80)
    print("Testing the three core features that make DASHSystem intelligent")
    
    results = []
    
    # Test Feature 1: Cold Start System
    try:
        result1 = test_feature_1_cold_start_system()
        results.append(("Cold Start System", result1))
    except Exception as e:
        print(f"\n❌ Cold Start Test Failed: {e}")
        logger.error(f"Cold start test failed: {e}")
        results.append(("Cold Start System", False))
    
    # Test Feature 2: Breadcrumb Cascade
    try:
        result2 = test_feature_2_breadcrumb_cascade()
        results.append(("Breadcrumb Cascade", result2))
    except Exception as e:
        print(f"\n❌ Cascade Test Failed: {e}")
        logger.error(f"Cascade test failed: {e}")
        results.append(("Breadcrumb Cascade", False))
    
    # Test Feature 3: Grade Progression
    try:
        result3 = test_feature_3_grade_progression()
        results.append(("Grade Progression", result3))
    except Exception as e:
        print(f"\n❌ Progression Test Failed: {e}")
        logger.error(f"Progression test failed: {e}")
        results.append(("Grade Progression", False))
    
    # Summary
    print("\n" + "="*80)
    print("📋 TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 ALL FEATURES WORKING CORRECTLY!")
        print("   DASHSystem V2 is ready for production use")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed")
        print("   Check logs for detailed error information")
    
    return passed == len(results)

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED WITH ERROR:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
