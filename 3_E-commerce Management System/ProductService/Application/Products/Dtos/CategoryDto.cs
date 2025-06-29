using System;
using System.Collections.Generic;

namespace ProductService.Application.Products.Dtos
{
    public class CategoryDto
    {
        public Guid Id { get; set; }
        public string Name { get; set; }
        public Guid? ParentCategoryId { get; set; }
        public List<CategoryDto> Children { get; set; } = new List<CategoryDto>();
    }
} 