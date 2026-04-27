import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock adminService
const mockFetchQuestions = vi.fn();
const mockApplyThemeDefaults = vi.fn();
vi.mock('@/services/adminService', () => ({
  fetchQuestions: (...args: unknown[]) => mockFetchQuestions(...args),
  applyThemeDefaults: (...args: unknown[]) => mockApplyThemeDefaults(...args),
}));

// Mock LifeEventTagEditor — simple stub
vi.mock('@/components/admin/LifeEventTagEditor', () => ({
  default: () => <div data-testid="life-event-tag-editor" />,
}));

// Mock constants
vi.mock('@/constants/lifeEventRegistry', () => ({
  VALID_PLACEHOLDERS: ['{spouse_name}', '{child_name}'],
}));

// Mock sonner toast
vi.mock('@/components/ui/sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Mock toastError
vi.mock('@/utils/toastError', () => ({
  toastError: vi.fn(),
}));

// Stub window.confirm
vi.stubGlobal('confirm', vi.fn(() => true));

import ThemeSettings from '@/pages/admin/ThemeSettings';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeQuestions(overrides: Record<string, unknown> = []) {
  return [
    {
      questionId: 'childhood-1',
      questionType: 'childhood',
      themeName: 'Childhood Memories',
      difficulty: 1,
      Valid: 1,
      questionText: 'What is your earliest memory?',
      requiredLifeEvents: ['school'],
      isInstanceable: false,
      instancePlaceholder: '',
      promptDescription: '',
      lastModifiedBy: 'admin@test.com',
      lastModifiedAt: '2025-01-01T00:00:00Z',
      ...overrides,
    },
  ];
}

// ---------------------------------------------------------------------------
// Task 8.4: Unit tests for ThemeSettings.tsx prompt description UI
// Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.10
// ---------------------------------------------------------------------------

describe('ThemeSettings prompt description UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders textarea in edit mode with correct placeholder text', async () => {
    mockFetchQuestions.mockResolvedValue(makeQuestions());
    render(<ThemeSettings />);

    await waitFor(() => expect(screen.getByText('childhood')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Edit Tags'));

    const textarea = screen.getByLabelText('Prompt description');
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveAttribute('placeholder', 'Describe the theme context for the AI interviewer...');
  });

  it('loads and displays the current promptDescription value', async () => {
    mockFetchQuestions.mockResolvedValue(
      makeQuestions({ promptDescription: 'Focus on early childhood experiences' })
    );
    render(<ThemeSettings />);

    await waitFor(() => expect(screen.getByText('childhood')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Edit Tags'));

    const textarea = screen.getByLabelText('Prompt description') as HTMLTextAreaElement;
    expect(textarea.value).toBe('Focus on early childhood experiences');
  });

  it('displays correct character count', async () => {
    const desc = 'A'.repeat(50);
    mockFetchQuestions.mockResolvedValue(makeQuestions({ promptDescription: desc }));
    render(<ThemeSettings />);

    await waitFor(() => expect(screen.getByText('childhood')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Edit Tags'));

    expect(screen.getByText('50/1000')).toBeInTheDocument();
  });

  it('disables Apply button when promptDescription exceeds 1000 characters', async () => {
    const longDesc = 'A'.repeat(1001);
    mockFetchQuestions.mockResolvedValue(makeQuestions({ promptDescription: longDesc }));
    render(<ThemeSettings />);

    await waitFor(() => expect(screen.getByText('childhood')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Edit Tags'));

    const applyButton = screen.getByRole('button', { name: /Apply to/i });
    expect(applyButton).toBeDisabled();
  });

  it('shows validation message when exceeding 1000 characters', async () => {
    const longDesc = 'A'.repeat(1001);
    mockFetchQuestions.mockResolvedValue(makeQuestions({ promptDescription: longDesc }));
    render(<ThemeSettings />);

    await waitFor(() => expect(screen.getByText('childhood')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Edit Tags'));

    expect(screen.getByText('Prompt description must be 1000 characters or fewer')).toBeInTheDocument();
  });

  it('includes promptDescription in the request payload on Apply', async () => {
    mockFetchQuestions.mockResolvedValue(
      makeQuestions({ promptDescription: 'Theme context for AI' })
    );
    mockApplyThemeDefaults.mockResolvedValue({ message: 'Updated', questionsUpdated: 1 });
    render(<ThemeSettings />);

    await waitFor(() => expect(screen.getByText('childhood')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Edit Tags'));

    const applyButton = screen.getByRole('button', { name: /Apply to/i });
    fireEvent.click(applyButton);

    await waitFor(() => {
      expect(mockApplyThemeDefaults).toHaveBeenCalledWith('childhood', expect.objectContaining({
        promptDescription: 'Theme context for AI',
      }));
    });
  });

  it('shows truncated description in non-edit summary when present', async () => {
    const longDesc = 'B'.repeat(150);
    mockFetchQuestions.mockResolvedValue(makeQuestions({ promptDescription: longDesc }));
    render(<ThemeSettings />);

    await waitFor(() => expect(screen.getByText('childhood')).toBeInTheDocument());

    // Should show first 100 chars + "..."
    const expected = 'B'.repeat(100) + '...';
    expect(screen.getByText((_content, element) => {
      return element?.textContent === `Prompt: ${expected}`;
    })).toBeInTheDocument();
  });

  it('shows "No prompt description" in non-edit summary when empty', async () => {
    mockFetchQuestions.mockResolvedValue(makeQuestions({ promptDescription: '' }));
    render(<ThemeSettings />);

    await waitFor(() => expect(screen.getByText('childhood')).toBeInTheDocument());

    expect(screen.getByText((_content, element) => {
      return element?.textContent === 'Prompt: No prompt description';
    })).toBeInTheDocument();
  });
});
