#!/bin/bash

echo "Testing detect-market-cycles service..."

# Test 1: Run the fredapi integration test
echo "Running fredapi integration test..."
sudo docker run --rm -e "FRED_API_KEY=${FRED_API_KEY:?Set FRED_API_KEY in your environment}" \
  -v $(pwd):/workspace \
  registry.alpha5.finance/datasources/detect-market-cycles:latest \
  python /workspace/test_fredapi.py

# Test 2: Interactive shell for manual testing
echo "Starting interactive shell for manual testing..."
sudo docker run --rm -it --name detect-market-cycles \
  -e "FRED_API_KEY=${FRED_API_KEY:?Set FRED_API_KEY in your environment}" \
  -v $(pwd):/workspace \
  registry.alpha5.finance/datasources/detect-market-cycles:latest bash

#-v /data/services/detect-market-cycles/logs:/workspace/logs \