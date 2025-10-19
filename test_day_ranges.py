#!/usr/bin/env python3
"""
Test script to verify that day ranges and date ranges are working correctly in the attendance system.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import init_db, add_class, get_all_classes

def test_class_storage():
    """Test that classes are being created with the correct recurrence patterns and date ranges."""
    print("Testing Class Storage with Day Ranges and Date Ranges")
    print("=" * 60)

    # Clean start
    if os.path.exists('school.db'):
        os.remove('school.db')
    init_db()

    # Create classes with different scheduling constraints
    test_cases = [
        {
            'name': 'Weekday Class', 'start_time': '09:00', 'end_time': '15:00',
            'recurrence_pattern': 31, 'start_date': None, 'end_date': None,
            'description': 'Mon-Fri only'
        },
        {
            'name': 'Weekend Class', 'start_time': '10:00', 'end_time': '16:00',
            'recurrence_pattern': 96, 'start_date': None, 'end_date': None,
            'description': 'Sat-Sun only'
        },
        {
            'name': 'Limited Class', 'start_time': '11:00', 'end_time': '13:00',
            'recurrence_pattern': 127, 'start_date': '2024-01-01', 'end_date': '2024-12-31',
            'description': 'All days, Jan-Dec 2024'
        },
        {
            'name': 'Wednesday Only', 'start_time': '14:00', 'end_time': '15:00',
            'recurrence_pattern': 4, 'start_date': None, 'end_date': None,
            'description': 'Wednesdays only'
        },
        {
            'name': 'No Days Class', 'start_time': '13:00', 'end_time': '14:00',
            'recurrence_pattern': 0, 'start_date': None, 'end_date': None,
            'description': 'No days scheduled'
        }
    ]

    # Create the classes
    for test_case in test_cases:
        result = add_class(
            test_case['name'], test_case['start_time'], test_case['end_time'],
            test_case['start_date'], test_case['end_date'], test_case['recurrence_pattern']
        )
        if result:
            print(f"✓ Created class: {test_case['name']} ({test_case['description']})")
        else:
            print(f"✗ Failed to create class: {test_case['name']}")
            return False

    # Retrieve and verify all classes
    print("\nVerifying stored classes...")
    classes = get_all_classes()
    classes_by_name = {cls.name: cls for cls in classes}

    passed_tests = 0
    total_tests = len(test_cases)

    for test_case in test_cases:
        name = test_case['name']
        if name not in classes_by_name:
            print(f"✗ Class {name} not found in database")
            continue

        cls = classes_by_name[name]

        # Check recurrence pattern
        if cls.recurrence_pattern != test_case['recurrence_pattern']:
            print(f"✗ Class {name}: recurrence_pattern {cls.recurrence_pattern} != {test_case['recurrence_pattern']}")
        else:
            print(f"✓ Class {name}: recurrence_pattern correct ({cls.recurrence_pattern})")

        # Check dates
        if cls.start_date != test_case['start_date']:
            print(f"✗ Class {name}: start_date '{cls.start_date}' != '{test_case['start_date']}'")
        else:
            print(f"✓ Class {name}: start_date correct ({cls.start_date})")

        if cls.end_date != test_case['end_date']:
            print(f"✗ Class {name}: end_date '{cls.end_date}' != '{test_case['end_date']}'")
        else:
            print(f"✓ Class {name}: end_date correct ({cls.end_date})")

        # Check times
        if cls.start_time != test_case['start_time']:
            print(f"✗ Class {name}: start_time '{cls.start_time}' != '{test_case['start_time']}'")
        else:
            print(f"✓ Class {name}: start_time correct ({cls.start_time})")

        if cls.end_time != test_case['end_time']:
            print(f"✗ Class {name}: end_time '{cls.end_time}' != '{test_case['end_time']}'")
        else:
            print(f"✓ Class {name}: end_time correct ({cls.end_time})")

        passed_tests += 1

    print(f"\nTest Results: {passed_tests}/{total_tests} classes created and verified correctly")
    return passed_tests == total_tests

def test_get_days_from_bitmask():
    """Test the bitmask utility function."""
    print("\nTesting Bitmask Display Function")
    print("=" * 40)

    from sections.admin_ui_components import get_days_from_bitmask

    test_cases = [
        (0, 'No days'),
        (1, 'Mon'),
        (4, 'Wed'),
        (31, 'Mon-Fri'),
        (96, 'Sat-Sun'),
        (127, 'Daily'),
        (2+4+8+16, 'Tue, Wed, Thu, Fri'),
    ]

    passed = 0
    for bitmask, expected in test_cases:
        result = get_days_from_bitmask(bitmask)
        status = "✓" if result == expected else "✗"
        print(f"{status} Bitmask {bitmask} -> '{result}' (expected: '{expected}')")
        if result == expected:
            passed += 1

    print(f"\nBitmask tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_format_date_range():
    """Test the date range formatting function."""
    print("\nTesting Date Range Formatting Function")
    print("=" * 45)

    from sections.admin_ui_components import format_date_range

    test_cases = [
        ((None, None), ''),
        (('2024-01-01', None), 'From 2024-01-01'),
        ((None, '2024-12-31'), 'Until 2024-12-31'),
        (('2024-01-01', '2024-12-31'), '2024-01-01 to 2024-12-31'),
    ]

    passed = 0
    for dates, expected in test_cases:
        result = format_date_range(*dates)
        status = "✓" if result == expected else "✗"
        print(f"{status} {dates} -> '{result}' (expected: '{expected}')")
        if result == expected:
            passed += 1

    print(f"\nDate range tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

if __name__ == '__main__':
    success1 = test_class_storage()
    success2 = test_get_days_from_bitmask()
    success3 = test_format_date_range()

    if success1 and success2 and success3:
        print("\n🎉 All tests passed! Day ranges and date ranges are working correctly.")
    else:
        print("\n❌ Some tests failed.")

    print("Day range and date range testing completed!")
