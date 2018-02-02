import React from 'react';
import PropTypes from 'prop-types';

export default class Dropdown extends React.Component {
    static propTypes = {
        toggle: PropTypes.func,
        closedFile: PropTypes.string,
        openFile: PropTypes.string,
        open: PropTypes.bool,
    };

    static defaultProps = {
        closedFile: 'next.png',
        openFile: 'dsc.png',
        open: false,
        closeOnClick: false,
    };

    state = {open: this.props.open};

    render() {
        return (
            <span style={{position: 'relative'}}>
                <img src={STATIC_URL + (this.open() ? this.props.openFile : this.props.closedFile)}
                    onClick={this.toggle_} />
            { this.open() ?
                (<div onClick={this.props.closeOnClick && this.toggle_}>
                    { this.props.children }
                </div>)
                :
                null
            }
            </span>
        );
    }

    open() {
        return this.props.toggle ? this.props.open : this.state.open;
    }

    toggle_ = () => {
        if (this.props.toggle) {
            this.props.toggle();
        } else {
            this.setState({open: !this.state.open});
        }
    }
}

