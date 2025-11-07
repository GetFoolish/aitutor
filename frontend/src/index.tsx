/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import './styles/global.css';
import reportWebVitals from './reportWebVitals';
import "./package/perseus/testing/perseus-init.tsx";
import { ChakraProvider, ColorModeScript, extendTheme } from '@chakra-ui/react';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { GameProvider } from './contexts/GameContext';
import { AppRouter } from './router';

const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    brand: {
      50: '#E6F2FF',
      100: '#BAD9FF',
      200: '#8DC1FF',
      300: '#61A8FF',
      400: '#3490FF',
      500: '#0877FF',
      600: '#0660CC',
      700: '#044899',
      800: '#023066',
      900: '#011833',
    },
  },
  styles: {
    global: {
      body: {
        bg: '#1c1f21',
        color: '#e1e2e3',
      },
    },
  },
});

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <>
    <ColorModeScript initialColorMode={theme.config.initialColorMode} />
    <ThemeProvider>
      <ChakraProvider theme={theme}>
        <AuthProvider>
          <GameProvider>
            <AppRouter />
          </GameProvider>
        </AuthProvider>
      </ChakraProvider>
    </ThemeProvider>
  </>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();