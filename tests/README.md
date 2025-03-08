# Baby Wise End-to-End Test Plan

This directory contains the end-to-end test plan for the Baby Wise system, focusing on verifying that the system correctly handles both informational queries and baby tracking commands.

## Test Files

- `e2e_test_plan.py`: Automated tests for the Baby Wise system
- `manual_e2e_test_plan.md`: Manual test plan for testers
- `run_e2e_tests.sh`: Shell script to run the automated tests

## Running the Tests

### Automated Tests

To run the automated tests, execute the following command from the `tests` directory:

```bash
./run_e2e_tests.sh
```

This script will:
1. Check if the server is running
2. Start the server if needed
3. Run the automated tests
4. Clean up resources

### Manual Tests

The manual test plan is designed for testers to verify the system's functionality through the user interface. To execute the manual tests:

1. Open the `manual_e2e_test_plan.md` file
2. Follow the steps for each test case
3. Document the results according to the pass/fail criteria

## Test Coverage

The test plan covers the following scenarios:

1. **Query About Baby Development**: Verifies that the system correctly responds to queries about baby feeding development
2. **Query About Baby Strollers**: Verifies that the system correctly responds to queries about baby stroller features
3. **Save Sleep Event**: Verifies that the system correctly processes and stores sleep tracking commands
4. **Offline Mode Tracking**: Verifies that the system handles tracking events when offline
5. **Multiple Consecutive Commands**: Verifies that the system correctly processes a sequence of tracking commands
6. **Request Summary**: Verifies that the system generates accurate summaries of tracked events

## Requirements

- Python 3.8+
- `requests` library
- Access to the Baby Wise API
- Environment variables set in `.env` file (optional)

## Troubleshooting

If you encounter issues running the tests:

1. Ensure the server is running and accessible
2. Check that the API endpoints are correctly configured
3. Verify that the environment variables are set correctly
4. Check the server logs for any errors

## Adding New Tests

To add new test cases:

1. For automated tests, add new test methods to the `BabyWiseE2ETests` class in `e2e_test_plan.py`
2. For manual tests, add new test cases to the `manual_e2e_test_plan.md` file following the existing format
3. Ensure that new tests follow the same structure and include clear pass/fail criteria 