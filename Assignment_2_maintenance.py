import streamlit as st
import graphviz

def k_out_of_n_availability_warm(n, k, s, lam, mu):
    #First we innitialize the unnormalized stationary distribution as 0 everywhere, and 1 in position 0
    pi_unnorm = [0.0] * (n + 1)
    pi_unnorm[0] = 1.0
    
    #Now from the birth-death process we know that pi(i+1) = pi(i)*(birth_rate / death_rate), so we iteratively update pi
    for i in range(n):
        birth_rate = min(n - i, s) * lam
        death_rate = (i+1) * mu
        pi_unnorm[i+1] = pi_unnorm[i] * (birth_rate / death_rate)
    
    #Now we only have to normalize to get to our stationary distribution
    norm_const = sum(pi_unnorm)
    pi = [x / norm_const for x in pi_unnorm]
    
    #Lastly we calculate the availability
    availability = sum(pi[i] for i in range(k, n + 1))
    return pi, availability

def k_out_of_n_availability_cold(n, k, s, lam, mu):
    #Same idea as in warm standby, but different death_rate
    pi_unnorm = [0.0] * (n + 1)
    pi_unnorm[0] = 1.0
    for i in range(n):
        birth_rate = min(n - i, s) * lam
        #In cold standby: if i < k then all i units are active; if i >= k then only k are active. 
        death_rate = i * mu if i < k else k * mu 
        pi_unnorm[i+1] = pi_unnorm[i] * (birth_rate / death_rate)
    
    norm_const = sum(pi_unnorm)
    pi = [x / norm_const for x in pi_unnorm]
    
    availability = sum(pi[j] for j in range(k, n + 1))
    return pi, availability

def total_cost(n, k, s, lam, mu, warm_standby, component_cost, repairman_cost, downtime_cost):
    if warm_standby:
        pi, availability = k_out_of_n_availability_warm(n, k, s, lam, mu)
    else:
        pi, availability = k_out_of_n_availability_cold(n, k, s, lam, mu)
    total_cost =  (n * component_cost) + (s * repairman_cost) + ((1-availability) * downtime_cost)
    return total_cost

def optimize_system(k, lam, mu, warm_standby, component_cost, repairman_cost, downtime_cost):
    best_n, best_s, min_cost = None, None, float('inf')
    n_max = 1000 #we limit n to 1000
    n = k
    improvement = True
    #we now iteratively increase n to find a local minimum, we can assume this minimum to be global by Ger's last announcement
    while improvement and n <= 1000: 
        #Now we iterate over all possible numbers of repairmen
        current_best_cost = float('inf')
        current_best_s = None
        for s in range(1, n):
            cost = total_cost(n, k, s, lam, mu, warm_standby, component_cost, repairman_cost, downtime_cost)
            if cost < current_best_cost:
                current_best_cost = cost
                current_best_s = s
        #Only update min_cost if the found current best cost beats the previous
        if current_best_cost < min_cost:
            min_cost = current_best_cost
            best_n = n
            best_s = current_best_s
            n += 1  # Increase n for the next iteration.
        else:
            improvement = False
    return best_n, best_s, min_cost

def visualize_birth_death(n, k, s, lam, mu, warm_standby):
    dot = graphviz.Digraph(comment="Birth-Death Process")
    # Set graph to horizontal layout
    dot.attr(rankdir="LR")
    # Add nodes for all states.
    for i in range(n+1):
        dot.node(str(i), f"State {i}")
    # Add birth transitions.
    for i in range(n):
        multiplier = min(n - i, s)
        birth_rate = multiplier * lam
        label_text = f"Birth: {multiplier}λ = {birth_rate:.2f}"
        dot.edge(str(i), str(i+1), label=label_text)
    # Add death transitions.
    for j in range(1, n+1):
        if warm_standby:
            death_rate = j * mu
            label_text = f"Death: {j}μ = {death_rate:.2f}"
        else:
            if j <= k:
                death_rate = j * mu
                label_text = f"Death: {j}μ = {death_rate:.2f}"
            else:
                death_rate = k * mu
                label_text = f"Death: {k}μ = {death_rate:.2f}"
        dot.edge(str(j), str(j-1), label=label_text)
    
    return dot


def main():
    st.title("K-out-of-N System Calculator")
    
    # User Inputs
    mu = st.number_input("Failure Rate (per unit time)", min_value=0.0001, value=0.1, format="%.4f")
    lam = st.number_input("Repair Rate (per unit time)", min_value=0.0001, value=0.5, format="%.4f")
    n = st.number_input("Total Number of Components (n)", min_value=1, value=5, step=1)
    k = st.number_input("Minimum Components for Functionality (k)", min_value=1, value=3, step=1)
    s = st.number_input("Number of Repairmen", min_value=1, value=1, step=1)
    warm_standby = st.checkbox("Use Warm Standby?", value=True)
    component_cost = st.number_input("Cost per component:", min_value=1, value=10)
    repairman_cost = st.number_input("Cost per repairman:", min_value=1, value=50)
    downtime_cost = st.number_input("Downtime cost per unit time:", min_value=1, value=100)
    
    if k > n:
        st.error("The system cannot require more components than available!")
        return
    
    # Compute stationary distribution and availability
    if warm_standby:
        pi, availability = k_out_of_n_availability_warm(n, k, s, lam, mu)
    else:
        pi, availability = k_out_of_n_availability_cold(n, k, s, lam, mu)
    
    st.write(f"### Birth-Death Process Graphic")
    if st.checkbox("Show Birth-Death Process Graph"):
        dot = visualize_birth_death(n, k, s, lam, mu, warm_standby)
        st.graphviz_chart(dot)
    
    # Display results
    st.write(f"### Results")
    st.write(f"**Fraction of time system is operational:** {availability:.4f}")
    st.write("**Stationary Distribution of States:**")
    st.bar_chart(pi)
    
    if st.button("Optimize Configuration"):
      best_n, best_s, min_cost = optimize_system(k, lam, mu, warm_standby, component_cost, repairman_cost, downtime_cost)
      st.success(f"Optimal number of components: {best_n}")
      st.success(f"Optimal number of repairmen: {best_s}")
      st.success(f"Minimum total cost: {min_cost:.2f}")
    
if __name__ == "__main__":
    main()
