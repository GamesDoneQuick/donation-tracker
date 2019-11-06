export function loadEventDetails(eventDetails) {
  // `event` doesn't have any other useful props for this page, so receivername
  // is pulled out and flattened into the details structure for the reducer.
  const {
    event: { receivername },
  } = eventDetails;

  return {
    type: 'eventsDetails/LOAD_EVENT_DETAILS',
    data: {
      ...eventDetails,
      receivername,
    },
  };
}
