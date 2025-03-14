# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import json

# Load quiz questions from cloud_security_data.json
def load_quiz_questions():
    try:
        with open('cloud_security_data.json', 'r') as file:
            data = json.load(file)
            return data.get('quiz_questions', [])
    except Exception as e:
        print(f"Error loading quiz questions: {e}")
        return []

def calculate_quiz_results(dispatcher: CollectingDispatcher, tracker: Tracker) -> List[Dict[Text, Any]]:
    score = float(tracker.get_slot("quiz_score") or 0)
    total_questions = float(tracker.get_slot("total_questions") or 5)
    
    # Calculate percentage score
    percentage = (score / total_questions) * 100
    
    # Provide feedback based on score
    if percentage >= 80:
        message = f"Excellent! You scored {score}/{total_questions} ({percentage:.1f}%). You have a strong understanding of cloud security concepts."
    elif percentage >= 60:
        message = f"Good job! You scored {score}/{total_questions} ({percentage:.1f}%). You have a good foundation in cloud security, but there's still room to learn more."
    else:
        message = f"You scored {score}/{total_questions} ({percentage:.1f}%). Consider reviewing cloud security concepts to improve your understanding."
    
    dispatcher.utter_message(text=message)
    
    # Reset quiz-related slots
    return [
        SlotSet("current_question", None),
        SlotSet("current_question_index", 0),
        SlotSet("quiz_score", 0),
        SlotSet("is_last_question", False)
    ]

class ActionAskQuestion(Action):
    def name(self) -> Text:
        return "action_ask_question"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get quiz questions
        quiz_questions = load_quiz_questions()
        
        if not quiz_questions:
            dispatcher.utter_message(text="I'm sorry, I couldn't load the quiz questions.")
            return [SlotSet("current_question", None)]
        
        # Set total questions
        total_questions = min(5, len(quiz_questions))
        
        # Get the first question
        first_question = quiz_questions[0]
        
        # Format the question with options
        question_text = f"1. {first_question['question']}\n\n"
        for option, text in first_question['options'].items():
            question_text += f"{option}. {text}\n"
        
        dispatcher.utter_message(text=question_text)
        
        # Check if this is the last question (should be false for first question)
        is_last_question = (total_questions == 1)
        
        # Set slots for the current question and index
        return [
            SlotSet("current_question", first_question),
            SlotSet("current_question_index", 0),
            SlotSet("quiz_score", 0),
            SlotSet("total_questions", total_questions),
            SlotSet("is_last_question", is_last_question)
        ]

class ActionValidateAnswer(Action):
    def name(self) -> Text:
        return "action_validate_answer"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get the current question
        current_question = tracker.get_slot("current_question")
        current_score = float(tracker.get_slot("quiz_score") or 0)
        
        if not current_question:
            dispatcher.utter_message(text="I'm sorry, there seems to be an issue with the quiz. Let's start over.")
            return [SlotSet("current_question", None)]
        
        # Get the last user message
        last_message = tracker.latest_message.get('text', '').strip().upper()
        
        # Extract the answer (assume it's a single letter A, B, C, or D)
        user_answer = None
        if last_message:
            if last_message.startswith('A'):
                user_answer = 'A'
            elif last_message.startswith('B'):
                user_answer = 'B'
            elif last_message.startswith('C'):
                user_answer = 'C'
            elif last_message.startswith('D'):
                user_answer = 'D'
        
        # Check if the answer is correct
        correct_answer = current_question.get('correct_answer', '')
        
        if user_answer == correct_answer:
            dispatcher.utter_message(text=f"Correct! {current_question.get('explanation', '')}")
            return [SlotSet("quiz_score", current_score + 1)]
        else:
            # If incorrect or invalid
            if user_answer:
                dispatcher.utter_message(text=f"That's not quite right. The correct answer is {correct_answer}: {current_question.get('explanation', '')}")
            else:
                dispatcher.utter_message(text=f"I couldn't understand your answer. The correct answer is {correct_answer}: {current_question.get('explanation', '')}")
            
            return []

class ActionAskNextQuestion(Action):
    def name(self) -> Text:
        return "action_ask_next_question"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Get the current state
        current_question_index = float(tracker.get_slot("current_question_index") or 0)
        total_questions = float(tracker.get_slot("total_questions") or 5)
        
        # Increment question index
        next_index = current_question_index + 1
        
        # Check if we're about to see the last question
        # Important: This is the question we're about to show, not the current one
        will_be_last_question = (next_index == total_questions - 1)
        
        # If we still have questions to ask
        if next_index < total_questions:
            # Load quiz questions
            quiz_questions = load_quiz_questions()
            
            if not quiz_questions or next_index >= len(quiz_questions):
                dispatcher.utter_message(text="I'm sorry, I couldn't load the next question.")
                return [SlotSet("current_question", None), SlotSet("is_last_question", False)]
            
            # Get the next question
            next_question = quiz_questions[int(next_index)]
            
            # Ask the question
            question_text = f"{int(next_index) + 1}. {next_question['question']}\n\n"
            for option, text in next_question['options'].items():
                question_text += f"{option}. {text}\n"
            
            dispatcher.utter_message(text=question_text)
            
            # Update slots
            return [
                SlotSet("current_question", next_question),
                SlotSet("current_question_index", next_index),
                SlotSet("is_last_question", will_be_last_question)
            ]
        else:
            # No more questions, show results
            return self.show_results(dispatcher, tracker)
    
    def show_results(self, dispatcher, tracker):
        return calculate_quiz_results(dispatcher, tracker)

class ActionQuizResults(Action):
    def name(self) -> Text:
        return "action_quiz_results"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Use the shared function to calculate and display results
        return calculate_quiz_results(dispatcher, tracker)
