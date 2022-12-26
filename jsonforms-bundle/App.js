import React, { useState, useMemo } from 'react';
import { JsonForms } from '@jsonforms/react';
import {
  materialCells,
  materialRenderers,
} from '@jsonforms/material-renderers';
import { makeStyles } from '@mui/styles';

const useStyles = makeStyles({
  container: {
    padding: '1em',
    width: '100%',
  },
  title: {
    textAlign: 'center',
    padding: '0.25em',
  },
  dataContent: {
    display: 'flex',
    justifyContent: 'center',
    borderRadius: '0.25em',
    backgroundColor: '#cecece',
    marginBottom: '1rem',
  },
  demoform: {
    margin: 'auto',
    padding: '1rem',
  },
});

const App = () => {
  const classes = useStyles();
  const [data, setData] = useState(initialData);
  const stringifiedData = useMemo(() => JSON.stringify(data, null, 2), [data]);

  return (
    React.createElement(
      JsonForms,
      {
        schema,
        uischema,
        data,
        renderers: materialRenderers,
        cells: materialCells,
        onChange: ({ errors, data }) => {
          setData(data);

          if (typeof onChange === 'function')
            onChange({ errors, data });
        }
      }
    )
  )
};

export default App;
