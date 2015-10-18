import React from 'react';

export default class Dropdown extends React.Component {
    constructor(props) {
        super(props);
        this.toggle = this.toggle.bind(this);
    }

    render() {
        return (
            <span style={{position: 'relative'}}>
                <img src={STATIC_URL + (this.props.open ? this.props.openFile : this.props.closedFile)}
                    onClick={this.toggle} />
            { this.props.open ?
                (<div>
                    { this.props.children }
                </div>)
                :
                null
            }
            </span>
        );
    }

    toggle() {
        this.props.toggle();
    }
}

Dropdown.propTypes = {
    toggle: React.PropTypes.func.isRequired,
};

Dropdown.defaultProps = {
    closedFile: 'next.png',
    openFile: 'dsc.png',
    open: false,
};
