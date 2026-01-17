/**
 * usePendingFeedback Hook
 *
 * Manages pending feedback with localStorage persistence and batch submission.
 * Uses a 4-second delay before submitting to allow users to correct misclicks.
 *
 * Features:
 * - Stores pending feedback in localStorage (survives page refresh)
 * - 4-second timer resets on each interaction
 * - Submits to API when timer fires
 * - Handles multiple messages with pending feedback
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/api/client';
import { PendingFeedback } from '@/types';

const STORAGE_KEY = 'pendingFeedback';
const SUBMIT_DELAY_MS = 4000; // 4 seconds

interface PendingFeedbackMap {
  [messageId: string]: PendingFeedback;
}

// Load pending feedback from localStorage
const loadFromStorage = (): PendingFeedbackMap => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
};

// Save pending feedback to localStorage
const saveToStorage = (data: PendingFeedbackMap): void => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Ignore storage errors
  }
};

// Clear pending feedback from localStorage
const clearFromStorage = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore storage errors
  }
};

export const usePendingFeedback = () => {
  const [pendingFeedback, setPendingFeedback] = useState<PendingFeedbackMap>(loadFromStorage);
  const [submittedFeedback, setSubmittedFeedback] = useState<Set<string>>(new Set());
  const timersRef = useRef<{ [messageId: string]: NodeJS.Timeout }>({});

  // Sync to localStorage whenever pendingFeedback changes
  useEffect(() => {
    saveToStorage(pendingFeedback);
  }, [pendingFeedback]);

  // Submit feedback for a specific message
  const submitFeedback = useCallback(async (messageId: string) => {
    const feedback = pendingFeedback[messageId];
    if (!feedback) return;

    try {
      await api.chat.submitFeedback(messageId, {
        contentRating: feedback.contentRating,
        styleRating: feedback.styleRating,
        contentFeedbackText: feedback.contentFeedbackText,
        styleFeedbackText: feedback.styleFeedbackText,
      });

      // Mark as submitted and remove from pending
      setSubmittedFeedback((prev) => new Set(prev).add(messageId));
      setPendingFeedback((prev) => {
        const updated = { ...prev };
        delete updated[messageId];
        return updated;
      });
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      // Keep in pending for retry
    }
  }, [pendingFeedback]);

  // Start or reset timer for a message
  const startTimer = useCallback((messageId: string) => {
    // Clear existing timer
    if (timersRef.current[messageId]) {
      clearTimeout(timersRef.current[messageId]);
    }

    // Start new timer
    timersRef.current[messageId] = setTimeout(() => {
      submitFeedback(messageId);
      delete timersRef.current[messageId];
    }, SUBMIT_DELAY_MS);
  }, [submitFeedback]);

  // Update pending feedback for a message (resets timer)
  const updateFeedback = useCallback((
    messageId: string,
    update: Partial<Omit<PendingFeedback, 'messageId' | 'timestamp'>>
  ) => {
    setPendingFeedback((prev) => {
      const existing = prev[messageId] || { messageId, timestamp: Date.now() };
      return {
        ...prev,
        [messageId]: {
          ...existing,
          ...update,
          timestamp: Date.now(),
        },
      };
    });

    // Reset timer
    startTimer(messageId);
  }, [startTimer]);

  // Set content rating
  const setContentRating = useCallback((messageId: string, rating: number) => {
    updateFeedback(messageId, { contentRating: rating });
  }, [updateFeedback]);

  // Set style rating
  const setStyleRating = useCallback((messageId: string, rating: number) => {
    updateFeedback(messageId, { styleRating: rating });
  }, [updateFeedback]);

  // Set content feedback text
  const setContentFeedbackText = useCallback((messageId: string, text: string) => {
    updateFeedback(messageId, { contentFeedbackText: text });
  }, [updateFeedback]);

  // Set style feedback text
  const setStyleFeedbackText = useCallback((messageId: string, text: string) => {
    updateFeedback(messageId, { styleFeedbackText: text });
  }, [updateFeedback]);

  // Get pending feedback for a message
  const getPendingFeedback = useCallback((messageId: string): PendingFeedback | undefined => {
    return pendingFeedback[messageId];
  }, [pendingFeedback]);

  // Check if feedback has been submitted for a message
  const isSubmitted = useCallback((messageId: string): boolean => {
    return submittedFeedback.has(messageId);
  }, [submittedFeedback]);

  // Check if there's a pending timer for a message
  const hasPendingTimer = useCallback((messageId: string): boolean => {
    return !!timersRef.current[messageId];
  }, []);

  // Submit all pending feedback immediately (for page unload)
  const submitAllPending = useCallback(async () => {
    const messageIds = Object.keys(pendingFeedback);
    await Promise.all(messageIds.map((id) => submitFeedback(id)));
  }, [pendingFeedback, submitFeedback]);

  // Handle page unload - submit all pending feedback
  useEffect(() => {
    const handleBeforeUnload = () => {
      // Use sendBeacon for reliable submission on page close
      const messageIds = Object.keys(pendingFeedback);
      for (const messageId of messageIds) {
        const feedback = pendingFeedback[messageId];
        if (feedback) {
          // Note: sendBeacon has limitations, this is best-effort
          // The localStorage persistence ensures we can retry on next load
          navigator.sendBeacon?.(
            `/api/clone/chat/message/${messageId}/feedback`,
            JSON.stringify({
              contentRating: feedback.contentRating,
              styleRating: feedback.styleRating,
              contentFeedbackText: feedback.contentFeedbackText,
              styleFeedbackText: feedback.styleFeedbackText,
            })
          );
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [pendingFeedback]);

  // On mount, submit any orphaned pending feedback from previous session
  useEffect(() => {
    const orphanedFeedback = loadFromStorage();
    const messageIds = Object.keys(orphanedFeedback);
    if (messageIds.length > 0) {
      // Submit orphaned feedback
      for (const messageId of messageIds) {
        submitFeedback(messageId);
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      Object.values(timersRef.current).forEach(clearTimeout);
    };
  }, []);

  return {
    pendingFeedback,
    setContentRating,
    setStyleRating,
    setContentFeedbackText,
    setStyleFeedbackText,
    getPendingFeedback,
    isSubmitted,
    hasPendingTimer,
    submitAllPending,
  };
};
