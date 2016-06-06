function intKeys(obj) {
    const result = Object.keys(obj);
    return result.map(key => {
        const ret = parseInt(key);
        return ret || key;
    });
}

Object.intKeys = intKeys;
