# evaluation helpers for knowledge agent
"""Evaluation metrics for Knowledge Agent."""

from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class AnswerQualityMetrics:
    """Metrics for answer quality evaluation."""
    relevance_score: float
    completeness_score: float
    accuracy_score: float
    clarity_score: float
    overall_score: float
    feedback: List[str]


class KnowledgeEvaluator:
    """
    Evaluates knowledge agent answer quality.
    """
    
    def __init__(self):
        self.evaluations = []
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        ground_truth: Optional[str] = None,
        sources_used: Optional[List[str]] = None,
    ) -> AnswerQualityMetrics:
        """
        Evaluate answer quality on multiple dimensions.
        
        Args:
            question: Original question
            answer: Generated answer
            ground_truth: Optional ground truth answer for comparison
            sources_used: Optional list of sources used
            
        Returns:
            Answer quality metrics
        """
        feedback = []
        
        # Relevance: Does answer address the question?
        relevance = self._evaluate_relevance(question, answer)
        if relevance < 0.7:
            feedback.append("Answer may not fully address the question")
        
        # Completeness: Is the answer complete?
        completeness = self._evaluate_completeness(answer)
        if completeness < 0.7:
            feedback.append("Answer seems incomplete or too brief")
        
        # Accuracy: Compare with ground truth if available
        accuracy = 1.0
        if ground_truth:
            accuracy = self._evaluate_accuracy(answer, ground_truth)
            if accuracy < 0.7:
                feedback.append("Answer differs significantly from expected")
        
        # Clarity: Is the answer clear and well-structured?
        clarity = self._evaluate_clarity(answer)
        if clarity < 0.7:
            feedback.append("Answer could be clearer or better structured")
        
        # Overall score (weighted average)
        overall = (
            relevance * 0.35 +
            completeness * 0.25 +
            accuracy * 0.25 +
            clarity * 0.15
        )
        
        metrics = AnswerQualityMetrics(
            relevance_score=relevance,
            completeness_score=completeness,
            accuracy_score=accuracy,
            clarity_score=clarity,
            overall_score=overall,
            feedback=feedback,
        )
        
        self.evaluations.append({
            "question": question,
            "answer": answer,
            "metrics": metrics,
        })
        
        return metrics
    
    def _evaluate_relevance(self, question: str, answer: str) -> float:
        """Evaluate if answer addresses the question."""
        # Extract key terms from question
        question_terms = set(
            word.lower()
            for word in re.findall(r'\w+', question)
            if len(word) > 3  # Skip short words
        )
        
        # Extract terms from answer
        answer_terms = set(
            word.lower()
            for word in re.findall(r'\w+', answer)
            if len(word) > 3
        )
        
        # Calculate overlap
        if not question_terms:
            return 0.5
        
        overlap = len(question_terms & answer_terms) / len(question_terms)
        
        # Scale to 0-1 range
        return min(1.0, overlap * 1.5)
    
    def _evaluate_completeness(self, answer: str) -> float:
        """Evaluate answer completeness."""
        # Check for "I don't have" or similar phrases
        uncertainty_phrases = [
            "i don't have",
            "i don't know",
            "not available",
            "cannot find",
        ]
        if any(phrase in answer.lower() for phrase in uncertainty_phrases):
            return 0.3
        
        # Length-based heuristic
        word_count = len(answer.split())
        
        if word_count < 20:
            return 0.4
        elif word_count < 50:
            return 0.7
        elif word_count < 100:
            return 0.9
        else:
            return 1.0
    
    def _evaluate_accuracy(self, answer: str, ground_truth: str) -> float:
        """Evaluate accuracy compared to ground truth."""
        # Simple word overlap metric
        answer_words = set(answer.lower().split())
        truth_words = set(ground_truth.lower().split())
        
        if not truth_words:
            return 1.0
        
        overlap = len(answer_words & truth_words) / len(truth_words)
        return min(1.0, overlap * 1.2)
    
    def _evaluate_clarity(self, answer: str) -> float:
        """Evaluate answer clarity and structure."""
        score = 1.0
        
        # Check for run-on sentences
        sentences = answer.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        if avg_sentence_length > 30:
            score -= 0.2
        
        # Check for formatting (bullet points, etc.)
        if '-' in answer or '•' in answer or '\n' in answer:
            score += 0.1
        
        # Check for polite language
        polite_phrases = ["please", "thank you", "happy to help", "glad to assist"]
        if any(phrase in answer.lower() for phrase in polite_phrases):
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def get_aggregate_metrics(self) -> Dict[str, float]:
        """Get aggregate metrics across all evaluations."""
        if not self.evaluations:
            return {}
        
        return {
            "avg_relevance": sum(e["metrics"].relevance_score for e in self.evaluations) / len(self.evaluations),
            "avg_completeness": sum(e["metrics"].completeness_score for e in self.evaluations) / len(self.evaluations),
            "avg_accuracy": sum(e["metrics"].accuracy_score for e in self.evaluations) / len(self.evaluations),
            "avg_clarity": sum(e["metrics"].clarity_score for e in self.evaluations) / len(self.evaluations),
            "avg_overall": sum(e["metrics"].overall_score for e in self.evaluations) / len(self.evaluations),
            "total_evaluations": len(self.evaluations),
        }
    
    def get_low_quality_answers(self, threshold: float = 0.6) -> List[Dict]:
        """Get answers with quality below threshold."""
        return [
            e for e in self.evaluations
            if e["metrics"].overall_score < threshold
        ]
    
    def reset(self):
        """Reset evaluation state."""
        self.evaluations = []


class RAGEvaluator:
    """
    Evaluates RAG system performance.
    """
    
    @staticmethod
    def evaluate_retrieval(
        query: str,
        retrieved_docs: List[str],
        relevant_docs: List[str],
    ) -> Dict[str, float]:
        """
        Evaluate retrieval quality.
        
        Args:
            query: Search query
            retrieved_docs: Documents retrieved by system
            relevant_docs: Ground truth relevant documents
            
        Returns:
            Retrieval metrics (precision, recall, F1)
        """
        retrieved_set = set(retrieved_docs)
        relevant_set = set(relevant_docs)
        
        if not retrieved_set or not relevant_set:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        
        # True positives
        tp = len(retrieved_set & relevant_set)
        
        # Precision
        precision = tp / len(retrieved_set) if retrieved_set else 0.0
        
        # Recall
        recall = tp / len(relevant_set) if relevant_set else 0.0
        
        # F1 Score
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "retrieved_count": len(retrieved_set),
            "relevant_count": len(relevant_set),
        }