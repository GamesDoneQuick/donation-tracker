import * as React from 'react';
import classNames from 'classnames';

import styles from './RadioList.mod.css';

const RadioListLooks = {
  INLINE: styles.lookInline,
  VERTICAL: styles.lookVertical,
  CUSTOM: styles.lookCustom,
};

type Option = {
  name: string,
  value: any,
  render?: ({
      name: string,
      value: any,
      selected: boolean,
      onSelect: () => void,
    }) => React.Element,
};

const RadioItem = (props) => {
  const {
    name,
    value,
    selected,
    onSelect
  } = props;

  const handleClick = React.useCallback((e) => {
    e.preventDefault();
    onSelect != null && onSelect(value);
  }, [onSelect]);

  return (
    <button className={classNames(styles.radioItem, {[styles.selectedItem]: selected})} onClick={handleClick}>
      {name}
    </button>
  );
};


const RadioList = (props) => {
  const {
    options,
    value,
    look=RadioListLooks.INLINE,
    onChange,
    renderOption=null,
    className,
  } = props;

  const handleClick = React.useCallback((value) => {
    onChange != null && onChange(value);
  }, [onChange]);

  return (
    <div className={classNames(styles.container, look, className)}>
      { look === RadioListLooks.CUSTOM
        ? options.map((option) => renderOption({
            ...option,
            key: option.value,
            selected: value === option.value,
            onSelect: handleClick,
          }))
        : options.map((option) =>
            <RadioItem
              {...option}
              key={option.value}
              selected={value === option.value}
              onSelect={handleClick}
            />
          )
      }
    </div>
  );
};

RadioList.Looks = RadioListLooks;

export default RadioList;
