# what this system do?
# reposibility: wire the component pieces: model class??, conntroller, flag_checker, state_planner, solution_builder, hint_gen together
# input: student logs, full private description file (description + flag), writeups/solutions file, other params
# load discriptions + solution
# if student path already on solution file (action matched_existing_graph) => skip controller, flag_checker, solution_builder, retrieve solution file, feed it into hint_gen
# if new solution path + start_from_scratch => dont feed student state into controller, update solution file
# if new solution path + continue_from_student_state => feed student state into controller, update solution file

# controller return handling based on "status"