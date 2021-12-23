_robot_target_comm = None


def set_global_robot_target_comm(robot_target_comm):
    global _robot_target_comm
    _robot_target_comm = robot_target_comm


def get_global_robot_target_comm():
    return _robot_target_comm
