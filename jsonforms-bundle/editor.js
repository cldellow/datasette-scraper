import { createTheme, CssBaseline, ThemeProvider } from '@mui/material';
import ReactDOM from 'react-dom';
import React from 'react';
import App from './App';

/**
 * Customize form so each control has more space
 */
const theme = createTheme({
  components: {
    MuiFormControl: {
      styleOverrides: {
        root: {
          margin: '0.8em 0',
        },
      }
    },
  },
});

ReactDOM.render(
  React.createElement(
    ThemeProvider,
    { theme },
    React.createElement(
      CssBaseline,
      null
    ),
    React.createElement(App, null),
  ),
  document.getElementById('editor')
)
