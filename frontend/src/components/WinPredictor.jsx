import { useMemo } from 'react'

/**
 * WinPredictor — live win probability bar based on current game state.
 * 
 * Probability is calculated using:
 * 1. Score differential (primary signal)
 * 2. Game progress (more weight as game advances)
 * 3. Sigmoid function to map score diff → probability
 */
export default function WinPredictor({ gameState }) {
    const { whitePct, blackPct, drawPct } = useMemo(() => {
        if (!gameState) return { whitePct: 50, blackPct: 50, drawPct: 0 }

        const ws = gameState.white_score || 0
        const bs = gameState.black_score || 0
        const filled = gameState.cells_filled || 0
        const total = gameState.total_cells || 49
        const progress = Math.min(filled / total, 1) // 0 → 1

        // If game is finished, show final result
        if (gameState.is_finished) {
            if (gameState.winner === 'draw') return { whitePct: 50, blackPct: 50, drawPct: 0 }
            if (gameState.winner === 'white') return { whitePct: 95, blackPct: 5, drawPct: 0 }
            return { whitePct: 5, blackPct: 95, drawPct: 0 }
        }

        const diff = ws - bs

        // Scale factor increases with game progress (early game = uncertain, late = confident)
        // At turn 1: k ≈ 0.05, at turn 50%: k ≈ 0.15, at turn 100%: k ≈ 0.3
        const k = 0.05 + progress * 0.25

        // Sigmoid: maps any score diff to 0–1 range
        const sigmoid = 1 / (1 + Math.exp(-k * diff))

        // Blend with 50% based on game progress (early = more uncertain)
        const confidence = Math.min(progress * 1.5, 1) // reaches full confidence at ~67% through
        const blended = 0.5 + (sigmoid - 0.5) * confidence

        let wPct = Math.round(blended * 100)
        wPct = Math.max(2, Math.min(98, wPct)) // Clamp to 2-98%
        const bPct = 100 - wPct

        return { whitePct: wPct, blackPct: bPct, drawPct: 0 }
    }, [gameState?.white_score, gameState?.black_score, gameState?.cells_filled, gameState?.is_finished])

    if (!gameState) return null

    const wName = gameState.player_white || 'White'
    const bName = gameState.player_black || 'Black'

    return (
        <div className="w-full mb-3">
            {/* Labels */}
            <div className="flex justify-between items-center mb-1">
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-white border border-slate-300" />
                    <span className="text-xs font-bold truncate max-w-[100px]" style={{ color: 'var(--text-primary)' }}>{wName}</span>
                    <span className="text-xs font-extrabold" style={{ color: whitePct > blackPct ? '#10b981' : 'var(--text-muted)' }}>
                        {whitePct}%
                    </span>
                </div>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                    style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                    WIN PREDICTOR
                </span>
                <div className="flex items-center gap-1.5">
                    <span className="text-xs font-extrabold" style={{ color: blackPct > whitePct ? '#10b981' : 'var(--text-muted)' }}>
                        {blackPct}%
                    </span>
                    <span className="text-xs font-bold truncate max-w-[100px]" style={{ color: 'var(--text-primary)' }}>{bName}</span>
                    <div className="w-3 h-3 rounded-full bg-red-600 border border-red-400" />
                </div>
            </div>
            {/* Bar */}
            <div className="w-full h-3 rounded-full overflow-hidden flex" style={{ background: 'var(--bg-secondary)' }}>
                <div
                    className="h-full transition-all duration-700 ease-out rounded-l-full"
                    style={{
                        width: `${whitePct}%`,
                        background: 'linear-gradient(90deg, #e2e8f0, #f8fafc)',
                        boxShadow: whitePct > 55 ? '0 0 8px rgba(255,255,255,0.3)' : undefined,
                    }}
                />
                <div
                    className="h-full transition-all duration-700 ease-out rounded-r-full"
                    style={{
                        width: `${blackPct}%`,
                        background: 'linear-gradient(90deg, #dc2626, #ef4444)',
                        boxShadow: blackPct > 55 ? '0 0 8px rgba(239,68,68,0.3)' : undefined,
                    }}
                />
            </div>
        </div>
    )
}
