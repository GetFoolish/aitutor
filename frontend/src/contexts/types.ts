interface ExamData {
    title: string
    total_questions: number
    expected_time: Date
} 

export type ExamAction = 
  | { type: 'SET_EXAM'; payload: any }
  | { type: 'RECORD_ANSWER'; payload: { questionId: string; answer: any } }
  | { type: 'GRADE_EXAM'; payload: { answerKey: any; gradingScheme: any } }
  | { type: 'RESET_EXAM' };

export type ExamContextType = {
  state: Exam;
  dispatch: React.Dispatch<ExamAction>;
};

export type UserAnswer = {
    questionId: string
    answer: any
    isCorrect?: boolean
}

export type Exam = {
    examData: ExamData | null
    userAnswers: Record<string, any>
    score: number | null
    isGraded: boolean
}