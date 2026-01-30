

def solve_timetable(subjects, availability, fixed_events, constraints):
    # build time slots
    # create variables: "study subject j in slot i"
    # add constraints: no overlaps, avoid fixed events, meet targets
    # maximise: weighted study time
    # return list of study blocks


blocks = solve_timetable(subjects, avails, fixed, constraints)
return render_template("timetable.html", blocks=blocks)
