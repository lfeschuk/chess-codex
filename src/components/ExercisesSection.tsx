import React, { useState, useEffect, useMemo } from 'react';
import { 
  Sparkles, 
  HelpCircle, 
  RotateCcw, 
  Trophy, 
  CheckCircle2, 
  Lock, 
  Activity, 
  Flame, 
  Award,
  BookOpen,
  ChevronRight,
  Eye,
  EyeOff,
  ArrowLeft,
  ArrowRight
} from 'lucide-react';
import { SampleBookPage, ParsedChessGame, ChessMove, SidelineVariation } from '../types';
import { ChessBoard } from './ChessBoard';

interface ExerciseScore {
  completed: boolean;
  score: number;
  maxScore: number;
  attempts: number;
}

interface ExercisesSectionProps {
  currentBook: { title: string; exercises: SampleBookPage[] };
  selectedExerciseId: string;
  setSelectedExerciseId: (id: string) => void;
  activeExercise: SampleBookPage | null;
  activeGame: ParsedChessGame;
  currentMoveIndex: number;
  setCurrentMoveIndex: (idx: number) => void;
  gameMoves: ChessMove[];
  isCorrectionMode: boolean;
  setIsCorrectionMode: (val: boolean) => void;
  solitairePlayer: 'W' | 'B' | 'both' | 'auto';
  setSolitairePlayer: (player: 'W' | 'B' | 'both' | 'auto') => void;
  solitaireStartFrom: 'opening' | 'puzzle';
  setSolitaireStartFrom: (val: 'opening' | 'puzzle') => void;
  correctionFeedback: { text: string; isCorrect: boolean | null };
  setCorrectionFeedback: (val: { text: string; isCorrect: boolean | null }) => void;
  resetSolitaire: () => void;
  solitaireFrontierIndex: number;
  solitaireSidelineFrontierIndex: number;
  activeSideline: SidelineVariation | null;
  activeSidelineMoveIndex: number;
  openingMoves: ChessMove[];
  handleCorrectMovePlay: (nextIdx: number) => void;
  handleIncorrectMovePlay: (playedSAN: string, expectedSAN: string) => void;
  handleAlternateSidelinePlayed: (sld: SidelineVariation) => void;
  getSidelinePrefixInitialMoves: (sideline: SidelineVariation) => string;
}

export const ExercisesSection: React.FC<ExercisesSectionProps> = ({
  currentBook,
  selectedExerciseId,
  setSelectedExerciseId,
  activeExercise,
  activeGame,
  currentMoveIndex,
  setCurrentMoveIndex,
  gameMoves,
  isCorrectionMode,
  setIsCorrectionMode,
  solitairePlayer,
  setSolitairePlayer,
  solitaireStartFrom,
  setSolitaireStartFrom,
  correctionFeedback,
  setCorrectionFeedback,
  resetSolitaire,
  solitaireFrontierIndex,
  solitaireSidelineFrontierIndex,
  activeSideline,
  activeSidelineMoveIndex,
  openingMoves,
  handleCorrectMovePlay,
  handleIncorrectMovePlay,
  handleAlternateSidelinePlayed,
  getSidelinePrefixInitialMoves,
}) => {
  const LOCAL_STORAGE_SCORES_KEY = 'chess_codex_quiz_scores_v1';
  
  // Quiz states
  const [attemptsCount, setAttemptsCount] = useState(0);
  const [hintRequested, setHintRequested] = useState(false);
  const [hintLevel, setHintLevel] = useState(0); // 0 = none, 1 = source square, 2 = source + dest squares
  const [exerciseMoveScore, setExerciseMoveScore] = useState(0);
  const [showMoveListAnyway, setShowMoveListAnyway] = useState(false); // allows revealing the moves list for review
  const [showFullText, setShowFullText] = useState(false);
  
  // Library scores states
  const [scores, setScores] = useState<Record<string, ExerciseScore>>(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_SCORES_KEY);
    return saved ? JSON.parse(saved) : {};
  });

  // Load tactical exercises
  const exercises = useMemo(() => {
    return currentBook.exercises.filter(ex => !ex.id.startsWith('game_') || ex.id === 'game_1_tactical_trap');
  }, [currentBook.exercises]);

  const currentIndex = currentBook.exercises.findIndex(e => e.id === selectedExerciseId);
  const prevExercise = currentIndex > 0 ? currentBook.exercises[currentIndex - 1] : null;
  const nextExercise = currentIndex >= 0 && currentIndex < currentBook.exercises.length - 1 ? currentBook.exercises[currentIndex + 1] : null;

  // Sync scores to localstorage
  useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_SCORES_KEY, JSON.stringify(scores));
  }, [scores]);

  // Activate quiz validation by default when this section loads
  useEffect(() => {
    setIsCorrectionMode(true);
    setSolitairePlayer('auto'); // Auto-detect by default in quiz
    setSolitaireStartFrom('puzzle'); // Start from puzzle position by default
    return () => {
      setIsCorrectionMode(false);
    };
  }, []);

  // Reset exercise-specific quiz states on exercise switch
  useEffect(() => {
    setAttemptsCount(0);
    setHintRequested(false);
    setHintLevel(0);
    setExerciseMoveScore(0);
    setShowMoveListAnyway(false);
  }, [selectedExerciseId]);

  // Expected move SAN index and metadata
  const nextExpectedIndex = currentMoveIndex + 1;
  const activeMovesList = activeSideline ? activeSideline.moves : gameMoves;
  const expectedMove = activeMovesList[nextExpectedIndex];

  // Request a hint
  const handleRequestHint = () => {
    if (nextExpectedIndex >= activeMovesList.length) return;
    
    setHintRequested(true);
    const nextLevel = Math.min(2, hintLevel + 1);
    setHintLevel(nextLevel);

    if (nextLevel === 1) {
      setCorrectionFeedback({
        text: `HINT: Look at the board! The square of the piece you need to move is now highlighted in amber.`,
        isCorrect: null
      });
    } else if (nextLevel === 2) {
      // Find the expected move detail
      const nextMove = activeMovesList[nextExpectedIndex];
      setCorrectionFeedback({
        text: `HINT: The piece needs to move to the blue-highlighted square. The commentary states: "${nextMove.commentary || 'Study the position closely.'}"`,
        isCorrect: null
      });
    }
  };

  // Intercept move corrections to calculate score
  const handleCorrectQuizMove = (idx: number) => {
    // Determine points gained for this move
    let points = 0;
    if (attemptsCount === 0 && !hintRequested) {
      points = 3;
    } else if (attemptsCount === 1 && !hintRequested) {
      points = 2;
    } else if (hintRequested) {
      points = 1;
    }

    const nextScore = exerciseMoveScore + points;
    setExerciseMoveScore(nextScore);

    // Call base handler to update board state index
    handleCorrectMovePlay(idx);

    // Reset move attempt state
    setAttemptsCount(0);
    setHintRequested(false);
    setHintLevel(0);

    // Determine active puzzle moves and resolved player role to calculate completion & max score
    const interactiveStartIndex = solitaireStartFrom === 'opening' ? 0 : openingMoves.length;
    const activePuzzleMoves = activeSideline ? activeSideline.moves : gameMoves.slice(interactiveStartIndex);
    
    let resolvedRole = solitairePlayer;
    if (solitairePlayer === 'auto') {
      resolvedRole = activePuzzleMoves[0]?.player || 'W';
    }

    // Indices of the player's moves in the activePuzzleMoves list
    const playerMovesIndices = activePuzzleMoves
      .map((m, i) => (resolvedRole === 'both' || m.player === resolvedRole) ? i : -1)
      .filter(i => i !== -1);

    const playedPuzzleIndex = activeSideline ? idx : idx - interactiveStartIndex;
    const lastPlayerMoveIndex = playerMovesIndices[playerMovesIndices.length - 1];

    const isCompleted = playedPuzzleIndex === lastPlayerMoveIndex;
    if (isCompleted) {
      // Maximum possible score (3 points per move the player actually guessed)
      const maxScore = Math.max(1, playerMovesIndices.length) * 3;
      
      setScores(prev => ({
        ...prev,
        [selectedExerciseId]: {
          completed: true,
          score: nextScore,
          maxScore,
          attempts: prev[selectedExerciseId]?.attempts ? prev[selectedExerciseId].attempts + 1 : 1
        }
      }));

      setCorrectionFeedback({
        text: `🎉 EXERCISE COMPLETED! You scored ${nextScore} out of ${maxScore} points! Success Rate: ${((nextScore / maxScore) * 100).toFixed(1)}%.`,
        isCorrect: true
      });
    }
  };

  const handleIncorrectQuizMove = (playedSAN: string, expectedSAN: string) => {
    setAttemptsCount(prev => prev + 1);
    handleIncorrectMovePlay(playedSAN, expectedSAN);
  };

  // Calculate overall stats
  const stats = useMemo(() => {
    let completedCount = 0;
    let totalScore = 0;
    let totalMaxScore = 0;
    
    exercises.forEach(ex => {
      const scoreObj = scores[ex.id];
      if (scoreObj?.completed) {
        completedCount++;
        totalScore += scoreObj.score;
        totalMaxScore += scoreObj.maxScore;
      }
    });

    const successRate = totalMaxScore > 0 ? (totalScore / totalMaxScore) * 100 : 0;

    return {
      completedCount,
      totalExercises: exercises.length,
      totalScore,
      totalMaxScore,
      successRate
    };
  }, [exercises, scores]);

  // Unlocked achievements based on score stats
  const achievements = useMemo(() => {
    const list = [];
    if (stats.completedCount > 0) {
      list.push({ title: 'First Blood', desc: 'Solved your first chess codex exercise.', icon: Flame });
    }
    if (stats.completedCount === stats.totalExercises && stats.totalExercises > 0) {
      list.push({ title: 'Grandmaster Tactics', desc: 'Completed all training sessions!', icon: Trophy });
    }
    if (stats.successRate >= 85 && stats.completedCount >= 3) {
      list.push({ title: 'Lightning Mind', desc: 'Maintain an 85%+ success score rate.', icon: Award });
    }
    const hasUsedHints = Object.keys(scores).some(key => {
      const s = scores[key];
      return s.completed && s.score < s.maxScore;
    });
    if (hasUsedHints) {
      list.push({ title: "Scholar's Path", desc: 'Leveraged hint suggestions to solve puzzles.', icon: Activity });
    }
    return list;
  }, [stats, scores]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 w-full">
      {/* LEFT COLUMN: Chessboard & Quiz Status */}
      <div className="lg:col-span-5 flex flex-col gap-6">
        <div className="bg-[#FAF8F5] border border-black/10 rounded-2xl p-6 shadow-sm text-left">
          <div className="flex justify-between items-center mb-4 border-b border-black/5 pb-3">
            <div>
              <span className="text-[10px] font-sans font-bold uppercase tracking-widest text-red-700 block mb-1">
                TACTICAL QUIZ ACTIVE
              </span>
              <h2 className="text-xl font-serif font-medium leading-tight text-[#1A1A1A]">
                {activeGame.white || 'White'} vs {activeGame.black || 'Black'}
              </h2>
            </div>
            
            {/* Active Quiz Score Meter */}
            <div className="bg-amber-50 border border-amber-900/10 rounded-lg px-3 py-1.5 text-center shrink-0">
              <span className="text-[9px] font-sans uppercase tracking-widest opacity-60 block font-bold text-amber-950">Quiz Score</span>
              <span className="text-lg font-mono font-bold text-amber-900">{exerciseMoveScore} pts</span>
            </div>
          </div>

          {/* Quiz Options Selector Panel */}
          <div className="grid grid-cols-2 gap-4 mb-4 bg-white/40 p-3 border border-black/5 rounded-xl text-xs">
            {/* Play As Selector */}
            <div className="flex flex-col gap-1 text-left">
              <span className="text-[9px] font-sans font-bold uppercase tracking-wider text-stone-500">
                Your Role
              </span>
              <select
                value={solitairePlayer}
                onChange={(e) => {
                  const val = e.target.value as 'W' | 'B' | 'both' | 'auto';
                  setSolitairePlayer(val);
                  setTimeout(() => resetSolitaire(), 0);
                }}
                className="bg-white border border-black/10 rounded px-2 py-1.5 text-xs text-[#1A1A1A] outline-none focus:border-amber-500 transition-all font-serif cursor-pointer"
              >
                <option value="auto">🤖 Auto-Detect Side</option>
                <option value="W">⚪ Play as White</option>
                <option value="B">⚫ Play as Black</option>
                <option value="both">🤝 Guess Both Sides</option>
              </select>
            </div>

            {/* Start From Selector */}
            <div className="flex flex-col gap-1 text-left">
              <span className="text-[9px] font-sans font-bold uppercase tracking-wider text-stone-500">
                Start Position
              </span>
              <select
                value={solitaireStartFrom}
                onChange={(e) => {
                  const val = e.target.value as 'opening' | 'puzzle';
                  setSolitaireStartFrom(val);
                }}
                className="bg-white border border-black/10 rounded px-2 py-1.5 text-xs text-[#1A1A1A] outline-none focus:border-amber-500 transition-all font-serif cursor-pointer"
              >
                <option value="puzzle">🧩 Puzzle Position</option>
                <option value="opening">🏁 Move 1 (From Start)</option>
              </select>
            </div>
          </div>

          {/* Full Book Chapter Passage Toggle & Reader (100% Text Display) */}
          <div className="mb-6">
            <button
              onClick={() => setShowFullText(!showFullText)}
              className="w-full flex items-center justify-between px-4 py-2.5 bg-amber-900/10 hover:bg-amber-900/15 border border-amber-900/20 rounded-xl text-xs font-serif font-bold text-amber-950 transition-all cursor-pointer shadow-2xs"
            >
              <span className="flex items-center gap-2">
                <BookOpen size={14} className="text-[#D97706]" />
                <span>📖 100% Book Chapter Passage & Text</span>
              </span>
              <span className="text-[10px] font-sans font-bold uppercase tracking-wider bg-white px-2 py-0.5 rounded border border-amber-900/10">
                {showFullText ? 'Hide Passage ▲' : 'Read Full Passage ▼'}
              </span>
            </button>

            {showFullText && (
              <div className="mt-2 p-5 bg-[#FAF4EB] border border-amber-900/20 rounded-xl font-serif text-sm text-stone-850 leading-relaxed max-h-[380px] overflow-y-auto shadow-inner whitespace-pre-wrap">
                {activeExercise?.textContext || "No chapter passage available for this section."}
              </div>
            )}
          </div>

          {/* Chessboard Component Wrapper */}
          <div className="w-full flex justify-center py-4 bg-white/40 border border-black/5 rounded-xl mb-6 shadow-2xs">
            <ChessBoard
              key={`quiz_${selectedExerciseId}_${activeSideline?.id || ''}_${hintLevel}`}
              initialMoves={activeSideline ? getSidelinePrefixInitialMoves(activeSideline) : ((solitaireStartFrom === 'puzzle' || activeGame.initial_moves?.includes('/')) ? activeGame.initial_moves : "")}
              gameMoves={activeSideline ? activeSideline.moves : gameMoves}
              currentMoveIndex={activeSideline ? activeSidelineMoveIndex : currentMoveIndex}
              solitaireFrontierIndex={solitaireFrontierIndex}
              solitaireSidelineFrontierIndex={solitaireSidelineFrontierIndex}
              activeSideline={activeSideline}
              isCorrectionMode={true}
              onCorrectMoveParsed={handleCorrectQuizMove}
              onIncorrectMoveParsed={handleIncorrectQuizMove}
              sidelines={activeGame.sidelines}
              onAlternateSidelinePlayed={handleAlternateSidelinePlayed}
              hintLevel={hintLevel}
            />
          </div>

          {/* Interactive HUD / Prompt Board */}
          <div className="space-y-4">
            <div className={`p-4 border rounded-xl text-xs leading-relaxed font-serif ${
              correctionFeedback.isCorrect === true
                ? 'bg-green-50/75 border-green-300 text-green-950 shadow-2xs'
                : correctionFeedback.isCorrect === false
                  ? 'bg-red-50/75 border-red-300 text-red-950 shadow-2xs'
                  : 'bg-white border-black/10 text-stone-900'
            }`}>
              <div className="flex items-start gap-2">
                <span className="text-sm select-none font-bold mt-0.5">
                  {correctionFeedback.isCorrect === true ? '✓' : correctionFeedback.isCorrect === false ? '✗' : 'ℹ'}
                </span>
                <div>
                  {correctionFeedback.text}
                </div>
              </div>
            </div>

            {/* Actions panel */}
            <div className="flex items-center justify-between gap-3 pt-2 border-t border-black/5">
              <button
                onClick={handleRequestHint}
                disabled={nextExpectedIndex >= activeMovesList.length}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-45 text-white text-[10px] uppercase font-sans tracking-wider font-bold transition-all rounded shadow-xs"
              >
                <HelpCircle size={13} />
                <span>Request Hint (Lv.{hintLevel})</span>
              </button>

              <button
                onClick={resetSolitaire}
                className="px-4 py-2.5 bg-white hover:bg-stone-50 border border-black/10 text-[#1A1A1A] text-[10px] uppercase font-sans tracking-wider font-bold transition-all rounded"
              >
                <RotateCcw size={12} className="inline mr-1" />
                <span>Reset</span>
              </button>
            </div>
            
            <div className="flex justify-between items-center text-[10px] text-stone-500 font-sans">
              <span>Attempts: {attemptsCount}</span>
              <span>Next play: {expectedMove ? `${expectedMove.move_number}.${expectedMove.player === 'W' ? 'White' : 'Black'}` : 'Exercise Complete'}</span>
            </div>
          </div>

          {/* Section / Page Navigation Bar */}
          <div className="flex items-center justify-between gap-3 pt-4 border-t border-black/10 mt-6 font-sans">
            <button
              onClick={() => prevExercise && setSelectedExerciseId(prevExercise.id)}
              disabled={!prevExercise}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 bg-stone-100 hover:bg-amber-100 disabled:opacity-40 disabled:hover:bg-stone-100 border border-stone-300/80 rounded-xl text-xs font-bold text-stone-800 transition-all cursor-pointer shadow-2xs truncate"
              title={prevExercise ? `Go to: ${prevExercise.title}` : "First section of volume"}
            >
              <ArrowLeft size={14} className="shrink-0 text-amber-900" />
              <span className="truncate">{prevExercise ? `⬅️ Prev: ${prevExercise.title}` : 'First Section'}</span>
            </button>

            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-stone-500 bg-white px-2.5 py-1 rounded-lg border border-stone-200 shrink-0">
              Section {currentIndex + 1} of {currentBook.exercises.length}
            </span>

            <button
              onClick={() => nextExercise && setSelectedExerciseId(nextExercise.id)}
              disabled={!nextExercise}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 bg-amber-900 hover:bg-amber-950 disabled:opacity-40 disabled:hover:bg-amber-900 text-white border border-amber-950 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-sm truncate"
              title={nextExercise ? `Go to: ${nextExercise.title}` : "Last section of volume"}
            >
              <span className="truncate">{nextExercise ? `Next: ${nextExercise.title} ➡️` : 'Last Section'}</span>
              <ArrowRight size={14} className="shrink-0 text-amber-200" />
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: Exercises grid & Progress Stats */}
      <div className="lg:col-span-7 flex flex-col gap-6 text-left">
        {/* Silman Imbalance Masterclass Hero Dashboard */}
        {activeExercise?.id.startsWith('silman_intro') && (
          <div className="bg-gradient-to-br from-stone-900 via-amber-950 to-stone-900 text-white border border-amber-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
            <span className="text-[10px] font-mono uppercase tracking-widest text-amber-400 font-bold block mb-1">
              ✨ SILMAN'S MASTER CLASS
            </span>
            <h3 className="text-2xl font-serif font-light tracking-tight text-white mb-2">
              The 7 Imbalances Roadmap
            </h3>
            <p className="text-xs font-serif text-stone-300 italic mb-4 leading-relaxed">
              "If you want to be successful, you have to base your moves and plans on the specific imbalance-oriented criteria that exist in the given position, not on your mood, tastes, and/or fears!" — Jeremy Silman
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {[
                { id: 'silman_diag_1', name: '♗ Superior Minor Piece', desc: 'Active vs Inactive' },
                { id: 'silman_diag_3', name: '♟ Pawn Structure', desc: 'Passed & Weak Pawns' },
                { id: 'silman_diag_5', name: '🗺️ Space Advantage', desc: 'Territorial Annexation' },
                { id: 'silman_diag_6', name: '👑 Material', desc: 'Philosophy of Greed' },
                { id: 'silman_diag_7', name: '🛣️ Key File Control', desc: 'Roads for Rooks' },
                { id: 'silman_diag_8', name: '🕳️ Weak Squares', desc: 'Homes for Horses' },
                { id: 'silman_diag_9', name: '⚡ Development & Initiative', desc: 'Pushing Your Agenda' },
                { id: 'silman_diag_11', name: '🎯 King Safety', desc: 'Dragging Down Monarchs' },
                { id: 'silman_diag_12', name: '⚖️ Statics vs Dynamics', desc: 'Long vs Short Term' },
              ].map((imb) => (
                <button
                  key={imb.id}
                  onClick={() => setSelectedExerciseId(imb.id)}
                  className="p-2.5 bg-white/5 hover:bg-amber-500/20 border border-white/10 hover:border-amber-500/50 rounded-xl text-left transition-all group cursor-pointer"
                >
                  <span className="text-xs font-serif font-bold text-amber-300 group-hover:text-white block truncate">{imb.name}</span>
                  <span className="text-[9px] font-sans text-stone-400 group-hover:text-amber-200 block truncate">{imb.desc}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Solve Tracker & Progress Stats */}
        <div className="bg-[#141414] text-white border border-white/5 rounded-2xl p-6 shadow-md">
          <span className="text-[10px] font-mono uppercase tracking-widest opacity-40 block mb-2">
            QUIZ INSIGHTS
          </span>
          
          <div className="grid grid-cols-3 gap-6 mb-6">
            <div className="bg-white/5 rounded-xl p-4 border border-white/5">
              <span className="text-[9px] font-mono uppercase tracking-widest opacity-40 block mb-1">Solved</span>
              <div className="text-2xl font-light tracking-tight text-white font-sans">
                {stats.completedCount} <span className="text-xs opacity-50 font-serif italic">/ {stats.totalExercises}</span>
              </div>
            </div>
            
            <div className="bg-white/5 rounded-xl p-4 border border-white/5">
              <span className="text-[9px] font-mono uppercase tracking-widest opacity-40 block mb-1">Total Score</span>
              <div className="text-2xl font-light tracking-tight text-white font-sans">
                {stats.totalScore} <span className="text-xs opacity-50 font-serif italic">/ {stats.totalMaxScore}</span>
              </div>
            </div>

            <div className="bg-white/5 rounded-xl p-4 border border-white/5">
              <span className="text-[9px] font-mono uppercase tracking-widest opacity-40 block mb-1">Success Rate</span>
              <div className="text-2xl font-light tracking-tight text-white font-sans">
                {stats.successRate.toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Unlock Achievements Panel */}
          <div>
            <span className="text-[9px] font-mono uppercase tracking-widest opacity-40 block mb-3">Unlocked Medals</span>
            {achievements.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {achievements.map((ach, idx) => {
                  const Icon = ach.icon;
                  return (
                    <div 
                      key={idx}
                      className="flex items-center gap-2 bg-[#D97706]/10 border border-[#D97706]/20 px-3 py-1.5 rounded-lg text-xs text-amber-300"
                      title={ach.desc}
                    >
                      <Icon size={12} className="text-[#D97706]" />
                      <span className="font-semibold">{ach.title}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-xs text-stone-500 italic font-serif">Solve exercises correctly to earn training medals!</div>
            )}
          </div>
        </div>

        {/* Exercises Selectable Directory */}
        <div className="bg-[#141414] text-white border border-white/5 rounded-2xl p-6 shadow-md flex-grow">
          <span className="text-[10px] font-mono uppercase tracking-widest opacity-40 block mb-2">
            QUIZ BOOK DIRECTORY
          </span>
          <h3 className="text-xl font-serif text-white font-light tracking-tight mb-4">
            Chapter Tactical Puzzles
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[180px] overflow-y-auto pr-1">
            {exercises.length > 0 ? (
              exercises.map(ex => {
                const isActive = ex.id === selectedExerciseId;
                const scoreObj = scores[ex.id];
                return (
                  <div
                    key={ex.id}
                    onClick={() => setSelectedExerciseId(ex.id)}
                    className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all flex flex-col justify-between ${
                      isActive
                        ? 'bg-white/10 border-white text-white font-semibold'
                        : 'bg-white/5 border-white/5 text-gray-400 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <div>
                      <div className="text-[11.5px] font-sans leading-tight line-clamp-1 flex items-center justify-between gap-2">
                        <span className={isActive ? 'text-white' : 'text-stone-300'}>{ex.title}</span>
                        {scoreObj?.completed ? (
                          <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                        ) : (
                          <Lock size={12} className="opacity-30 shrink-0" />
                        )}
                      </div>
                      <div className="text-[9.5px] font-serif italic mt-1 opacity-60 line-clamp-1">{ex.description}</div>
                    </div>

                    {scoreObj?.completed && (
                      <div className="text-[9px] font-mono text-emerald-400 font-bold mt-2 pt-2 border-t border-white/5">
                        Score: {scoreObj.score} / {scoreObj.maxScore} pts
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="p-8 border border-dashed border-white/10 rounded col-span-2 text-center text-xs text-gray-500 italic">
                No exercises registered inside this book. Import some first!
              </div>
            )}
          </div>
        </div>

        {/* Option to show moves list for study after puzzle attempt */}
        <div className="bg-[#FAF8F5] border border-black/10 rounded-2xl p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase tracking-widest text-stone-500 font-bold">
              👁 Review Answer Key
            </span>
            <button
              onClick={() => setShowMoveListAnyway(!showMoveListAnyway)}
              className="flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-stone-50 border border-black/10 rounded text-[9.5px] font-sans uppercase font-bold tracking-wider cursor-pointer"
            >
              {showMoveListAnyway ? <EyeOff size={11} /> : <Eye size={11} />}
              <span>{showMoveListAnyway ? 'Hide Move Log' : 'Reveal Move Log'}</span>
            </button>
          </div>
          
          {showMoveListAnyway && (
            <div className="space-y-1 bg-black/90 p-3 rounded-xl border border-black/10 max-h-[140px] overflow-y-auto text-left font-mono">
              {gameMoves.map((m, index) => (
                <div key={index} className="text-xs text-stone-400 flex items-center gap-2">
                  <span className="w-8 text-[10px] text-stone-600 text-right">{m.move_number}{m.player === 'W' ? '.' : '...'}</span>
                  <span className="px-1 py-0.2 bg-stone-900 rounded text-amber-400 font-bold shrink-0">{m.move}</span>
                  <span className="text-[11px] text-stone-400 truncate max-w-[400px]">{m.commentary}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
