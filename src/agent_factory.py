async def get_agent_for_query(self, query: str) -> BaseAgent:
    print("\n=== DEBUG: Agent Selection Start ===")
    print(f"Incoming query: {query}")
    
    # FIRST: Check for gear-specific terms and force BabyGearAgent
    gear_terms = ["stroller", "car seat", "crib", "עגלה"]
    if any(term in query.lower() for term in gear_terms):
        for agent in self.agents:
            if isinstance(agent, BabyGearAgent):
                print("DEBUG: Gear term found - using BabyGearAgent")
                return agent
    
    # Only calculate other agents' confidence if no gear terms found
    agent_scores = []
    for agent in self.agents:
        confidence = await agent.can_handle_query(query, [])
        agent_scores.append((agent, confidence))
        print(f"DEBUG: {agent.name} confidence = {confidence}")
    
    selected_agent, confidence = max(agent_scores, key=lambda x: x[1])
    print(f"DEBUG: Selected {selected_agent.name} with confidence {confidence}")
    return selected_agent 