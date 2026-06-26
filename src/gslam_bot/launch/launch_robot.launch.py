import os
import xacro
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    pkg_name = 'gslam_bot'
    pkg_share = get_package_share_directory(pkg_name)
    urdf_path = os.path.join(pkg_share, 'urdf', 'two_wheel_robot.urdf.xacro')
    robot_description = xacro.process_file(urdf_path).toxml()
    world_path = os.path.join(pkg_share, 'worlds', 'empty_world.world')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('gazebo_ros'),
                'launch', 'gazebo.launch.py'
            )
        ),
        launch_arguments={
            'world': world_path,
            'gui': 'true'
        }.items()
    )
    
    odom_relay = Node(
    package='topic_tools',
    executable='relay',
    name='odom_relay',
    arguments=['/diff_drive_controller/odom', '/odom'],
    output='screen'
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }]
    )

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'gslam_bot'],
        output='screen'
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
    )

    diff_drive_spawner = Node(
    package='controller_manager',
    executable='spawner',
    arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
    remappings=[
        ('/diff_drive_controller/odom', '/odom'),
        ('/diff_drive_controller/cmd_vel_unstamped', '/cmd_vel'),
    ],
    )

    teleop = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        output='screen',
        remappings=[('/cmd_vel', '/diff_drive_controller/cmd_vel_unstamped')],
        prefix='xterm -e',
    )

    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        TimerAction(period=3.0, actions=[spawn_entity]),
        odom_relay,
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_entity,
                on_exit=[joint_state_broadcaster_spawner],
            )
        ),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[diff_drive_spawner],
            )
        ),
        teleop,
    ])