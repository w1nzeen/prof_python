from tech_manager.models import Tech
from tech_manager.services import (search_by_model, 
                                   sort_by_vendor, 
                                   avg_price, 
                                   find_most_expensive_tech,
                                   filter_by_price_range, 
                                   price_of_all_tech)

def create_demo_tech_list() -> list[Tech]:
    return [
        Tech(inventory_number="001", type="Laptop", vendor="Dell", model="XPS 13", price=999.99),
        Tech(inventory_number="002", type="Smartphone", vendor="Apple", model="iPhone 13", price=799.99),
        Tech(inventory_number="003", type="Tablet", vendor="Samsung", model="Galaxy Tab S7", price=649.99),
        Tech(inventory_number="004", type="Laptop", vendor="HP", model="Spectre x360", price=1199.99),
        Tech(inventory_number="005", type="Smartphone", vendor="Google", model="Pixel 6", price=599.99),
    ]

def print_tech_list(tech_list: list[Tech]) -> None:
    for tech in tech_list:
        print(f"Inventory Number: {tech.inventory_number}, Type: {tech.type}, Vendor: {tech.vendor}, Model: {tech.model}, Price: ${tech.price:.2f}")



def print_menu() -> None:
    print("\nTech Manager Menu:")
    print("1. View all tech items")
    print("2. Search by model")
    print("3. Sort by vendor")
    print("4. Calculate average price")
    print("5. Find the most expensive tech item")
    print("6. Filter by price range")
    print("7. Calculate total price of all tech items")
    print("8. Exit")



def main() -> None:
    tech_list = create_demo_tech_list()
    
    choice = 0

    while choice != 8: 
        
        print_menu()
        choice = int(input("Enter your choice: "))

        if choice == 1:
            print("\nAll Tech Items:")
            print_tech_list(tech_list)
        elif choice == 2:
            model = input("Enter the model to search for: ")
            search_results = search_by_model(tech_list, model)
            print("\nSearch Results:")
            print_tech_list(search_results)
        elif choice == 3:
            sorted_tech = sort_by_vendor(tech_list)
            print("\nSorted by Vendor:")
            print_tech_list(sorted_tech)
        elif choice == 4:
            average_price = avg_price(tech_list)
            print(f"\nAverage Price of Tech Items: ${average_price:.2f}")
        elif choice == 5:
            most_expensive = find_most_expensive_tech(tech_list)
            if most_expensive:
                print(f"\nMost Expensive Tech Item:\nInventory Number: {most_expensive.inventory_number}, Type: {most_expensive.type}, Vendor: {most_expensive.vendor}, Model: {most_expensive.model}, Price: ${most_expensive.price:.2f}")
        elif choice == 6:
            min_price = float(input("Enter minimum price: "))
            max_price = float(input("Enter maximum price: "))
            filtered_tech = filter_by_price_range(tech_list, min_price, max_price)
            print("\nFiltered by Price Range:")
            print_tech_list(filtered_tech)
        elif choice == 7:
            total_price = price_of_all_tech(tech_list)
            print(f"\nTotal Price of All Tech Items: ${total_price:.2f}")
        elif choice == 8:
            print("Exiting the program.")
        else:
            print("Invalid choice. Please try again.")


    if __name__ == "__main__":
        main()