import React, { useState, useMemo } from 'react';
import { JsonForms } from '@jsonforms/react';
// import { materialCells, materialRenderers } from '@jsonforms/material-renderers';
import { vanillaCells, vanillaRenderers } from '@jsonforms/vanilla-renderers';


const App = () => {
  const [data, setData] = useState(initialData);
  const stringifiedData = useMemo(() => JSON.stringify(data, null, 2), [data]);

  return (
    React.createElement(
      JsonForms,
      {
        schema,
        uischema,
        data,
//        renderers: materialRenderers,
//        cells: materialCells,
        renderers: vanillaRenderers,
        cells: vanillaCells,
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
