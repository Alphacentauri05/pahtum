import { useState, useEffect, useRef } from 'react'

export default function GameBoard({ board, boardSize, currentPlayer, onCellClick, disabled, lastMove }) {
    const [hoveredCell, setHoveredCell] = useState(null)

    return (
        <div className="flex flex-col items-center gap-4">
            {/* Column labels (1..N) */}
            <div className="flex gap-1" style={{ width: 'fit-content' }}>
                <div className="w-6 h-6" /> {/* Spacer for row labels */}
                {Array.from({ length: boardSize }, (_, i) => (
                    <div
                        key={i}
                        className="flex items-center justify-center text-xs font-bold"
                        style={{
                            width: `${Math.min(48, 340 / boardSize)}px`,
                            height: '24px',
                            color: 'var(--text-muted)',
                        }}
                    >
                        {i + 1}
                    </div>
                ))}
            </div>

            {/* Board grid with row labels (A..G) */}
            {Array.from({ length: boardSize }, (_, row) => (
                <div key={row} className="flex gap-1 items-center">
                    {/* Row label */}
                    <div
                        className="flex items-center justify-center text-xs font-bold"
                        style={{
                            width: '24px',
                            height: `${Math.min(48, 340 / boardSize)}px`,
                            color: 'var(--text-muted)',
                        }}
                    >
                        {String.fromCharCode('A'.charCodeAt(0) + row)}
                    </div>

                    {/* Cells */}
                    {Array.from({ length: boardSize }, (_, col) => {
                        const cell = board?.[row]?.[col] || '.'
                        const isOccupied = cell !== '.'
                        const isLastMove = lastMove && lastMove.row === row && lastMove.col === col
                        const isHovered = hoveredCell?.row === row && hoveredCell?.col === col

                        return (
                            <div
                                key={col}
                                className={`board-cell ${isOccupied ? 'occupied' : ''}`}
                                style={{
                                    width: `${Math.min(48, 340 / boardSize)}px`,
                                    height: `${Math.min(48, 340 / boardSize)}px`,
                                    borderColor: isLastMove
                                        ? '#f59e0b'
                                        : isHovered && !isOccupied && !disabled
                                            ? '#3b82f6'
                                            : undefined,
                                    boxShadow: isLastMove ? '0 0 12px rgba(245, 158, 11, 0.4)' : undefined,
                                }}
                                onMouseEnter={() => !isOccupied && !disabled && setHoveredCell({ row, col })}
                                onMouseLeave={() => setHoveredCell(null)}
                                onClick={() => !isOccupied && !disabled && onCellClick?.(row, col)}
                            >
                                {isOccupied && (
                                    <div
                                        className={`stone ${cell === 'W' ? 'white-stone' : 'black-stone'} ${isLastMove ? 'stone-enter' : ''}`}
                                    />
                                )}
                                {!isOccupied && isHovered && !disabled && (
                                    <div
                                        className={`stone ${currentPlayer === 'W' ? 'white-stone' : 'black-stone'}`}
                                        style={{ opacity: 0.3 }}
                                    />
                                )}
                            </div>
                        )
                    })}
                </div>
            ))}
        </div>
    )
}
