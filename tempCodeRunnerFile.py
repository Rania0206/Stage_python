class ScheduleGenerator:
    def __init__(self):
        self.timeslots = []
        self.resources = []
        self.events = []
        self.constraints = []

    def generate(self):
        # Generation: assign each event to consecutive slots where all resources are available
        results = []
        alerts = []
        used_slots = set()
        
        # Split work slots into 1-hour slots
        slots_1h = []
        for slot in self.timeslots:
            start_h = int(slot['start'].split(':')[0])
            end_h = int(slot['end'].split(':')[0])
            for h in range(start_h, end_h):
                slots_1h.append({
                    'day': slot['day'],
                    'start': f"{h:02d}:00",
                    'end': f"{h+1:02d}:00"
                })
        
        # Determine placement preference
        preference = "none"
        if self.constraints:
            constraint = self.constraints[0]['type']
            if "early" in constraint:
                preference = "early"
            elif "late" in constraint:
                preference = "late"
        
        for evt in self.events:
            event_duration = int(evt['duration'])  # Duration in hours
            found = False
            candidates = []
            
            # Look for consecutive slots of the required duration
            for i in range(len(slots_1h) - event_duration + 1):
                consecutive_slots = slots_1h[i:i+event_duration]
                
                # Check that all consecutive slots are available for all resources
                ok = True
                for slot in consecutive_slots:
                    for resource_name in evt['resources']:
                        r = next((r for r in self.resources if r['name'] == resource_name), None)
                        if not r:
                            ok = False
                            break
                        # Check if resource is available on this slot OR if the slot is within its availability period
                        available = False
                        for avail_slot in r['availability']:
                            if avail_slot['day'] == slot['day']:
                                avail_start = int(avail_slot['start'].split(':')[0])
                                avail_end = int(avail_slot['end'].split(':')[0])
                                slot_start = int(slot['start'].split(':')[0])
                                slot_end = int(slot['end'].split(':')[0])
                                # The slot must be included in the availability
                                if slot_start >= avail_start and slot_end <= avail_end:
                                    available = True
                                    break
                        if not available:
                            ok = False
                            break
                    if not ok:
                        break
                
                # Check that these slots are not already used
                if ok:
                    for slot in consecutive_slots:
                        if (slot['day'], slot['start'], slot['end']) in used_slots:
                            ok = False
                            break
                
                if ok:
                    candidates.append(consecutive_slots)
            
            # Choose the best candidate according to preference
            if candidates:
                if preference == "early":
                    # Take the first candidate (earliest)
                    consecutive_slots = candidates[0]
                elif preference == "late":
                    # Take the last candidate (latest)
                    consecutive_slots = candidates[-1]
                else:
                    # Take the first available candidate
                    consecutive_slots = candidates[0]
                
                # Place the event
                first_slot = consecutive_slots[0]
                last_slot = consecutive_slots[-1]
                for resource_name in evt['resources']:
                    results.append({
                        'event': evt['name'],
                        'day': first_slot['day'],
                        'start': first_slot['start'],
                        'end': last_slot['end'],
                        'resource': resource_name
                    })
                # Mark all slots as used
                for slot in consecutive_slots:
                    used_slots.add((slot['day'], slot['start'], slot['end']))
                found = True
            
            if not found:
                alerts.append(f"Unable to schedule '{evt['name']}' ({evt['duration']}h): not enough consecutive slots available for all resources.")
        
        return results, alerts

if __name__ == "__main__":
    root = tk.Tk()
    app = ScheduleGeneratorApp(root)
    root.mainloop()