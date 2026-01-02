# evaluation helpers for intent agent
"""Evaluation metrics for Intent Agent."""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from agents.intent.schemas import IntentType


@dataclass
class IntentEvaluationMetrics:
    """Metrics for intent classification performance."""
    accuracy: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1_score: Dict[str, float]
    confusion_matrix: Dict[str, Dict[str, int]]
    total_samples: int


class IntentEvaluator:
    """
    Evaluates intent classification performance.
    """
    
    def __init__(self):
        self.predictions = []
        self.ground_truth = []
    
    def add_prediction(
        self,
        predicted: IntentType,
        actual: IntentType,
        confidence: float,
    ):
        """Add a prediction for evaluation."""
        self.predictions.append({
            "predicted": predicted,
            "actual": actual,
            "confidence": confidence,
        })
        self.ground_truth.append(actual)
    
    def calculate_metrics(self) -> IntentEvaluationMetrics:
        """Calculate evaluation metrics."""
        if not self.predictions:
            return IntentEvaluationMetrics(
                accuracy=0.0,
                precision={},
                recall={},
                f1_score={},
                confusion_matrix={},
                total_samples=0,
            )
        
        # Calculate accuracy
        correct = sum(
            1 for p in self.predictions
            if p["predicted"] == p["actual"]
        )
        accuracy = correct / len(self.predictions)
        
        # Get all unique intents
        all_intents = set(p["actual"] for p in self.predictions)
        all_intents.update(p["predicted"] for p in self.predictions)
        
        # Calculate per-intent metrics
        precision = {}
        recall = {}
        f1_score = {}
        confusion_matrix = {
            intent: {other: 0 for other in all_intents}
            for intent in all_intents
        }
        
        for intent in all_intents:
            # True positives, false positives, false negatives
            tp = sum(
                1 for p in self.predictions
                if p["predicted"] == intent and p["actual"] == intent
            )
            fp = sum(
                1 for p in self.predictions
                if p["predicted"] == intent and p["actual"] != intent
            )
            fn = sum(
                1 for p in self.predictions
                if p["predicted"] != intent and p["actual"] == intent
            )
            
            # Precision
            precision[intent] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            
            # Recall
            recall[intent] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            
            # F1 Score
            p = precision[intent]
            r = recall[intent]
            f1_score[intent] = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
            
            # Confusion matrix
            for p in self.predictions:
                if p["actual"] == intent:
                    confusion_matrix[intent][p["predicted"]] += 1
        
        return IntentEvaluationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            confusion_matrix=confusion_matrix,
            total_samples=len(self.predictions),
        )
    
    def get_low_confidence_predictions(
        self,
        threshold: float = 0.7,
    ) -> List[Dict]:
        """Get predictions with confidence below threshold."""
        return [
            p for p in self.predictions
            if p["confidence"] < threshold
        ]
    
    def get_misclassifications(self) -> List[Dict]:
        """Get all misclassified examples."""
        return [
            p for p in self.predictions
            if p["predicted"] != p["actual"]
        ]
    
    def reset(self):
        """Reset evaluation state."""
        self.predictions = []
        self.ground_truth = []


class IntentTestSet:
    """
    Test dataset for intent classification.
    """
    
    @staticmethod
    def get_test_cases() -> List[Tuple[str, IntentType]]:
        """Get standard test cases for intent classification."""
        return [
            # Order Status
            ("Where is my order #12345?", IntentType.ORDER_STATUS),
            ("Track my shipment", IntentType.ORDER_STATUS),
            ("When will my package arrive?", IntentType.ORDER_STATUS),
            
            # Product Info
            ("What are the specs of the XYZ product?", IntentType.PRODUCT_INFO),
            ("Do you have this in blue?", IntentType.PRODUCT_INFO),
            ("How much does the ABC cost?", IntentType.PRODUCT_INFO),
            
            # Ticket Creation
            ("My product is broken", IntentType.TICKET_CREATION),
            ("I need help with setup", IntentType.TICKET_CREATION),
            ("This isn't working properly", IntentType.TICKET_CREATION),
            
            # Account Management
            ("I forgot my password", IntentType.ACCOUNT_MANAGEMENT),
            ("How do I update my profile?", IntentType.ACCOUNT_MANAGEMENT),
            ("Can't log into my account", IntentType.ACCOUNT_MANAGEMENT),
            
            # Returns & Refunds
            ("I want to return this", IntentType.RETURNS_REFUNDS),
            ("How do I get a refund?", IntentType.RETURNS_REFUNDS),
            ("Cancel my order", IntentType.RETURNS_REFUNDS),
            
            # General Inquiry
            ("What are your business hours?", IntentType.GENERAL_INQUIRY),
            ("Do you ship internationally?", IntentType.GENERAL_INQUIRY),
            ("Tell me about your company", IntentType.GENERAL_INQUIRY),
            
            # Greeting
            ("Hello!", IntentType.GREETING),
            ("Hi there", IntentType.GREETING),
            ("Hey, I need help", IntentType.GREETING),
            
            # Escalation
            ("I want to speak to a manager", IntentType.ESCALATION),
            ("This is ridiculous, get me a human", IntentType.ESCALATION),
            ("Connect me with a real person", IntentType.ESCALATION),
        ]
    
    @staticmethod
    def get_ambiguous_cases() -> List[str]:
        """Get test cases that should require clarification."""
        return [
            "I have a question",
            "Can you help me?",
            "Something's wrong",
            "I need assistance",
        ]