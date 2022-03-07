import React from 'react';

import { Ad, Interstitial, Interview, Model, ModelFields, Run } from '@common/Models';
import { sortItems } from '@common/Ordered';
import { ServerError } from '@common/Server';
import TableRowErrorDisplay from '@common/TableRowErrorDisplay';
import Body from './Body';

import styles from './index.mod.css';

interface Props {
  saveItem: (key: string, fields: Partial<ModelFields>) => void;
  changeableModels: string[];
  saveError: ServerError | null;
  interstitials: Array<Interview | Ad>;
  runs: Run[];
  moveInterstitial: ((sourceItem: Interstitial, destinationItem: Interstitial | Run) => void) | null;
}

interface State {
  sortedItems: Array<Interview | Ad | Run>;
}

export default class InterstitialEditorTable extends React.PureComponent<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { sortedItems: [] };
  }

  static getDerivedStateFromProps(props: Props) {
    return { sortedItems: sortItems([...props.interstitials, ...props.runs]) };
  }

  render() {
    const { sortedItems } = this.state;
    const { saveItem, saveError } = this.props;

    return (
      <table className={styles['root']}>
        <thead>
          {saveError ? <TableRowErrorDisplay error={saveError} /> : null}
          <tr className={styles['row--speedrun']}>
            <th>Run</th>
            <th colSpan={4}>Name</th>
            <th>Start Time</th>
            <th>End Time</th>
            <th>Setup</th>
            <th>Length</th>
          </tr>
          <tr className={styles['row--ad']}>
            <th>Ads</th>
            <th>Sponsor Name</th>
            <th>Ad Name</th>
            <th>Ad Type</th>
            <th colSpan={4}>Filename</th>
            <th>Length</th>
          </tr>
          <tr className={styles['row--interview']}>
            <th>Interviews</th>
            <th>Subject</th>
            <th>Interviewers</th>
            <th>Interviewees</th>
            <th>Producer</th>
            <th>Camera Operator</th>
            <th>Social Media</th>
            <th>Clips</th>
            <th>Length</th>
          </tr>
        </thead>
        <Body sortedItems={sortedItems} saveItem={saveItem} canEdit={this.canEdit} />
      </table>
    );
  }

  canEdit = (model: Model) => {
    return this.props.changeableModels.indexOf(model.model) !== -1;
  };

  // onDragEnd = (result: DropResult) => {
  //   const { moveInterstitial } = this.props;
  //   const { sortedItems } = this.state;
  //   if (
  //     !result.destination ||
  //     result.destination.index === 0 ||
  //     result.source.index === result.destination.index ||
  //     !moveInterstitial
  //   ) {
  //     return;
  //   }
  //
  //   const sourceItem = sortedItems[result.source.index];
  //   const destinationItem = sortedItems[result.destination.index];
  //   moveInterstitial(sourceItem as Interstitial, destinationItem);
  // };
}
