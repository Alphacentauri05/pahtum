import { createContext, useContext, useState, useEffect } from 'react'

const ThemeContext = createContext()

export function ThemeProvider({ children }) {
    const [dark, setDark] = useState(() => {
        const stored = localStorage.getItem('pahtum-theme')
        return stored ? stored === 'dark' : true // Default dark
    })

    useEffect(() => {
        document.documentElement.classList.toggle('dark', dark)
        localStorage.setItem('pahtum-theme', dark ? 'dark' : 'light')
    }, [dark])

    const toggle = () => setDark(d => !d)

    return (
        <ThemeContext.Provider value={{ dark, toggle }}>
            {children}
        </ThemeContext.Provider>
    )
}

export const useTheme = () => useContext(ThemeContext)
