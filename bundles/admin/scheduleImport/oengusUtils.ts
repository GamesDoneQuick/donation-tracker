export const parseOengusTime = (
  time: string,
): {
  hours: number;
  minutes: number;
  seconds: number;
} => {
  const resultTime = {
    hours: 0,
    minutes: 0,
    seconds: 0,
  };

  const regResult = time.match(/([0-9]{1,}(H|M|S))/g);

  if (regResult) {
    regResult.forEach(result => {
      if (result.includes('H')) {
        resultTime.hours = parseInt(result.replace('H', '')) || 0;
      }
      if (result.includes('M')) {
        resultTime.minutes = parseInt(result.replace('M', '')) || 0;
      }
      if (result.includes('S')) {
        resultTime.seconds = parseInt(result.replace('S', '')) || 0;
      }
    });
  }

  return resultTime;
};
